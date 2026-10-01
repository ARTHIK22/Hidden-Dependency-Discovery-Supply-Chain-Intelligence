from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db
from app.demo_data import seed_demo_data
from app.main import app
from app.models import Base, Entity, Investigation, Relationship, Report


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    def override_db() -> Generator[Session, None, None]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.state.risk_api_test_sessions = factory
    monkeypatch.setattr(settings, "jwt_secret_key", "risk-api-test-secret-with-at-least-32-bytes")
    monkeypatch.setattr(settings, "database_url", None)
    with factory() as db:
        seed_demo_data(db)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        del app.state.risk_api_test_sessions
        engine.dispose()


def _register(client: TestClient, label: str) -> tuple[dict[str, str], str]:
    email = f"{label}-{uuid4()}@example.test"
    response = client.post("/api/auth/register", json={
        "full_name": label,
        "email": email,
        "password": "risk-api-password-42",
    })
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, response.json()["user"]["id"]


def _create_investigation(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/api/investigations", headers=headers, json={
        "goal": "Find dependencies behind Example Product for an authorization fixture.",
        "depth": "standard",
    })
    assert response.status_code == 201
    return response.json()["investigation"]["id"]


def test_risk_and_report_routes_enforce_investigation_ownership(client: TestClient) -> None:
    owner, _ = _register(client, "Owner")
    outsider, _ = _register(client, "Outsider")
    investigation_id = _create_investigation(client, owner)

    factory = app.state.risk_api_test_sessions
    with factory() as db:
        demo_id = db.scalar(select(Investigation.id).where(Investigation.demo_mode.is_(True)))
        assert demo_id is not None
    assert client.post(f"/api/investigations/{demo_id}/analyze-risk", headers=owner).status_code == 409

    assert client.get(f"/api/investigations/{investigation_id}/risk-analysis", headers=owner).status_code == 200
    assert client.post(f"/api/investigations/{investigation_id}/analyze-risk", headers=outsider).status_code == 404
    assert client.get(f"/api/investigations/{investigation_id}/risk-analysis", headers=outsider).status_code == 404
    assert client.get(f"/api/investigations/{investigation_id}/risks", headers=outsider).status_code == 404

    report_response = client.post("/api/reports", headers=owner, json={"investigation_id": investigation_id})
    assert report_response.status_code == 201
    report_id = report_response.json()["id"]
    assert client.get(f"/api/reports/{report_id}", headers=owner).status_code == 200
    assert client.get(f"/api/reports/{report_id}/export?format=json", headers=owner).status_code == 200
    assert client.get(f"/api/reports/{report_id}", headers=outsider).status_code == 404
    assert client.get(f"/api/reports/{report_id}/export?format=csv", headers=outsider).status_code == 404


def test_report_generation_failure_preserves_investigation_state_and_records_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner, _ = _register(client, "ReportFailureOwner")
    investigation_id = _create_investigation(client, owner)
    factory = app.state.risk_api_test_sessions
    investigation_uuid = UUID(investigation_id)
    with factory() as db:
        investigation = db.get(Investigation, investigation_uuid)
        assert investigation is not None
        investigation.status = "RISK_ANALYZED"
        investigation.progress = 95
        investigation.risk_analysis = {"snapshot_id": "saved-snapshot"}
        db.add(Entity(name="Preserved entity", entity_type="supplier", investigation_id=investigation.id))
        db.commit()

    def fail_render(_report_data: dict[str, object]) -> str:
        raise ValueError("private renderer detail")

    monkeypatch.setattr("app.services.report_service._render_report", fail_render)
    response = client.post("/api/reports", headers=owner, json={"investigation_id": investigation_id})
    assert response.status_code == 500
    assert response.json() == {"detail": "Report generation failed"}
    assert "private renderer detail" not in response.text
    with factory() as db:
        investigation = db.get(Investigation, investigation_uuid)
        assert investigation is not None
        assert investigation.status == "RISK_ANALYZED"
        assert investigation.progress == 95
        assert investigation.risk_analysis == {"snapshot_id": "saved-snapshot"}
        assert investigation.lifecycle_events[-1]["type"] == "report_generation_failed"
        assert db.scalar(select(Entity.id).where(Entity.investigation_id == investigation_uuid, Entity.name == "Preserved entity")) is not None
        assert db.scalar(select(Report.id).where(Report.investigation_id == investigation_uuid)) is None


def test_graph_response_is_bounded_and_reports_truncation(client: TestClient) -> None:
    owner, _ = _register(client, "GraphLimitOwner")
    factory = app.state.risk_api_test_sessions
    with factory() as db:
        demo = db.scalar(select(Investigation).where(Investigation.demo_mode.is_(True)))
        assert demo is not None
        db.add_all([
            Entity(name=f"Graph capacity fixture {index}", entity_type="company", investigation_id=demo.id)
            for index in range(30)
        ])
        db.commit()

    response = client.get("/api/graph?limit=25", headers=owner)
    assert response.status_code == 200
    graph = response.json()
    assert len(graph["nodes"]) <= 25
    assert len(graph["edges"]) <= 50
    assert graph["has_more"] is True
    assert graph["has_more_entities"] is True
    assert graph["limit"] == 25

    next_page = client.get("/api/graph?limit=25&offset=25", headers=owner)
    assert next_page.status_code == 200
    assert next_page.json()["offset"] == 25
    assert next_page.json()["has_more_entities"] is False
    assert 0 < len(next_page.json()["nodes"]) <= 25


def test_shared_demo_alert_receipts_and_all_watch_target_types_are_user_scoped(client: TestClient) -> None:
    first, _ = _register(client, "First")
    second, _ = _register(client, "Second")
    investigation_id = _create_investigation(client, first)

    alerts_before = client.get("/api/alerts?unread_only=true", headers=first).json()["items"]
    second_alerts_before = client.get("/api/alerts?unread_only=true", headers=second).json()["items"]
    assert len(alerts_before) == len(second_alerts_before) == 2
    alert_id = alerts_before[0]["id"]
    assert client.patch(f"/api/alerts/{alert_id}/read", headers=first).status_code == 200
    assert len(client.get("/api/alerts?unread_only=true", headers=first).json()["items"]) == 1
    assert len(client.get("/api/alerts?unread_only=true", headers=second).json()["items"]) == 2
    assert client.patch("/api/alerts/read-all", headers=first).status_code == 204
    assert client.get("/api/alerts?unread_only=true", headers=first).json()["items"] == []
    assert len(client.get("/api/alerts?unread_only=true", headers=second).json()["items"]) == 2

    factory = app.state.risk_api_test_sessions
    with factory() as db:
        demo = db.scalar(select(Investigation).where(Investigation.demo_mode.is_(True)))
        entity_id = db.scalar(select(Entity.id).where(Entity.investigation_id == demo.id))
        relationship_id = db.scalar(select(Relationship.id).where(Relationship.investigation_id == demo.id))
        assert demo is not None and entity_id is not None and relationship_id is not None

    targets = [
        {"target_type": "entity", "target_id": str(entity_id)},
        {"target_type": "relationship", "target_id": str(relationship_id)},
        {"target_type": "investigation", "target_id": investigation_id},
        {"target_type": "risk_condition", "target_id": investigation_id, "risk_threshold": 65,
         "condition_json": {"metric": "overall_risk", "operator": "gte", "threshold": 65}},
    ]
    created_ids: set[str] = set()
    for target in targets:
        response = client.post("/api/watchlist", headers=first, json=target)
        assert response.status_code == 201, response.text
        created_ids.add(response.json()["id"])
    first_items = client.get("/api/watchlist", headers=first).json()["items"]
    second_items = client.get("/api/watchlist", headers=second).json()["items"]
    assert created_ids <= {item["id"] for item in first_items}
    assert created_ids.isdisjoint({item["id"] for item in second_items})

    personal_id = next(iter(created_ids))
    assert client.delete(f"/api/watchlist/items/{personal_id}", headers=second).status_code == 404
    assert client.delete(f"/api/watchlist/items/{personal_id}", headers=first).status_code == 204
    demo_watch = next(item for item in second_items if item["is_demo"])
    assert client.delete(f"/api/watchlist/items/{demo_watch['id']}", headers=second).status_code == 404
