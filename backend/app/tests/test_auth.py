from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db
from app.demo_data import seed_demo_data
from app.main import app
from app.models import Alert, Base, Entity, Evidence, Investigation, Relationship, Risk
from app.services.auth_service import hash_password, verify_password


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    def override_db() -> Generator[Session, None, None]:
        with test_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(settings, "jwt_secret_key", "test-only-secret-with-at-least-32-bytes")
    monkeypatch.setattr(settings, "database_url", None)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_password_hashing_uses_non_reversible_hash() -> None:
    encoded = hash_password("CorrectHorseBatteryStaple-42")
    assert encoded != "CorrectHorseBatteryStaple-42"
    assert verify_password("CorrectHorseBatteryStaple-42", encoded)
    assert not verify_password("wrong-password", encoded)


def test_health_contract_exposes_boolean_demo_mode(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["demo_mode"] is settings.development_demo_mode


def test_register_login_me_and_logout_revoke_session(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Demo User",
            "email": " Demo.User@example.test ",
            "password": "correct-horse-42",
        },
    )
    assert response.status_code == 201
    created = response.json()
    assert created["user"]["email"] == "demo.user@example.test"
    assert "password" not in created["user"]
    token = created["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/auth/me", headers=auth).json()["full_name"] == "Demo User"
    assert client.get("/api/dashboard/summary").status_code == 401
    assert client.get("/api/dashboard/summary", headers=auth).status_code == 200

    login = client.post(
        "/api/auth/login",
        json={"email": "DEMO.USER@example.test", "password": "correct-horse-42"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == created["user"]["id"]
    assert client.post(
        "/api/auth/login",
        json={"email": "demo.user@example.test", "password": "wrong-password"},
    ).status_code == 401

    assert client.post("/api/auth/logout", headers=auth).status_code == 204
    assert client.get("/api/auth/me", headers=auth).status_code == 401


def test_missing_invalid_and_expired_tokens_are_rejected(client: TestClient) -> None:
    account = client.post(
        "/api/auth/register",
        json={"full_name": "Token Tester", "email": "token-tester@example.test", "password": "token-test-password"},
    )
    assert account.status_code == 201
    user_id = account.json()["user"]["id"]
    expired = jwt.encode(
        {"sub": user_id, "ver": 0, "exp": datetime.now(timezone.utc) - timedelta(seconds=5)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"}).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_registration_rejects_duplicate_and_invalid_password(client: TestClient) -> None:
    account = {"full_name": "Demo", "email": "demo@example.test", "password": "long-enough"}
    assert client.post("/api/auth/register", json=account).status_code == 201
    assert client.post("/api/auth/register", json=account).status_code == 409
    too_short = {**account, "email": "other@example.test", "password": "short"}
    assert client.post("/api/auth/register", json=too_short).status_code == 422


def test_demo_seed_is_idempotent_and_explicitly_unverified(client: TestClient) -> None:
    # The fixture uses the test client's isolated in-memory SQLite database.
    db_dependency = app.dependency_overrides[get_db]
    db_generator = db_dependency()
    test_db = next(db_generator)
    try:
        first = seed_demo_data(test_db)
        second = seed_demo_data(test_db)
        assert first.id == second.id
        assert first.demo_mode is True
        assert test_db.query(Entity).filter_by(investigation_id=first.id).count() == 6
        assert test_db.query(Relationship).filter_by(investigation_id=first.id).count() == 6
        assert test_db.query(Evidence).count() == 6
        assert test_db.query(Risk).filter_by(investigation_id=first.id).count() == 3
        assert test_db.query(Alert).filter_by(investigation_id=first.id).count() == 2
        assert test_db.query(Investigation).count() == 1
        assert all("DEMO" in row.excerpt for row in test_db.query(Evidence).all())

        registration = client.post(
            "/api/auth/register",
            json={"full_name": "Fixture Reader", "email": "fixture@example.test", "password": "test-password-42"},
        )
        headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
        risk_list = client.get("/api/risks", headers=headers).json()
        assert sorted(item["score"] for item in risk_list["items"]) == [51, 64, 72]
        summary = client.get("/api/risks/summary", headers=headers).json()
        assert summary["average_score"] == pytest.approx(62.33)
        evidence = client.get("/api/evidence", headers=headers).json()
        assert {item["confidence"] for item in evidence["items"]} == {0.35}
    finally:
        db_generator.close()
