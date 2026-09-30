from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.main import app


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    test_sessions = sessionmaker(bind=test_engine, class_=Session, expire_on_commit=False)

    def override_db():
        with test_sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def test_auth_investigation_evidence_graph_report_and_exports(client: TestClient):
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": "analyst@example.com", "password": "SecurePass123", "full_name": "Test Analyst"},
    )
    assert registration.status_code == 201, registration.text
    token = registration.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": "ANALYST@example.com", "password": "SecurePass123"})
    assert login.status_code == 200, login.text
    assert client.post("/api/v1/auth/login", json={"email": "analyst@example.com", "password": "incorrect"}).status_code == 401

    investigation = client.post(
        "/api/v1/investigations", headers=headers, json={"name": "Supplier review"}
    )
    assert investigation.status_code == 201, investigation.text
    investigation_id = investigation.json()["id"]

    supplier = client.post(
        "/api/v1/entities", headers=headers, json={"name": "Supplier One", "entity_type": "supplier"}
    )
    buyer = client.post(
        "/api/v1/entities", headers=headers, json={"name": "Buyer One", "entity_type": "company"}
    )
    assert supplier.status_code == buyer.status_code == 201
    alias = client.post(
        f"/api/v1/entities/{buyer.json()['id']}/aliases", headers=headers,
        json={"alias": "Buyer Incorporated", "alias_type": "legal_name"},
    )
    assert alias.status_code == 201, alias.text
    assert len(client.get("/api/v1/entities", headers=headers, params={"q": "Buyer Incorporated"}).json()) == 1

    source = client.post(
        "/api/v1/sources", headers=headers,
        json={"name": "Analyst-provided filing", "source_type": "manual", "reliability_score": 0.95},
    )
    assert source.status_code == 201, source.text
    relationship = client.post(
        "/api/v1/relationships", headers=headers,
        json={"source_entity_id": supplier.json()["id"], "target_entity_id": buyer.json()["id"], "relationship_type": "SUPPLIES", "confidence_score": 0.7},
    )
    assert relationship.status_code == 201, relationship.text

    second_buyer = client.post(
        "/api/v1/entities", headers=headers, json={"name": "Buyer Two", "entity_type": "company"}
    )
    shared_relationship = client.post(
        "/api/v1/relationships", headers=headers,
        json={"source_entity_id": supplier.json()["id"], "target_entity_id": second_buyer.json()["id"], "relationship_type": "SUPPLIES"},
    )
    assert shared_relationship.status_code == 201, shared_relationship.text
    risk = client.get("/api/v1/risks/analysis", headers=headers)
    assert risk.status_code == 200
    assert any(item["category"] == "common_dependency" for item in risk.json()["risks"])

    evidence = client.post(
        "/api/v1/evidence", headers=headers,
        json={"investigation_id": investigation_id, "source_id": source.json()["id"], "relationship_id": relationship.json()["id"], "title": "Filing excerpt", "content": "Supplier One supplies Buyer One.", "evidence_type": "filing", "confidence_score": 0.9},
    )
    assert evidence.status_code == 201, evidence.text
    verified = client.post(f"/api/v1/relationships/{relationship.json()['id']}/verify", headers=headers)
    assert verified.status_code == 200
    assert verified.json()["verification"]["status"] == "verified"

    graph = client.get(f"/api/v1/graph/{supplier.json()['id']}", headers=headers)
    assert graph.status_code == 200
    assert len(graph.json()["nodes"]) == 3
    assert len(graph.json()["edges"]) == 2
    report = client.post(f"/api/v1/reports/investigations/{investigation_id}", headers=headers)
    assert report.status_code == 200, report.text
    assert report.json()["evidence_count"] == 1
    assert client.get("/api/v1/exports/graph.json", headers=headers).status_code == 200
    assert client.get("/api/v1/exports/relationships.csv", headers=headers).status_code == 200
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
    watched = client.post(f"/api/v1/watchlists/{supplier.json()['id']}", headers=headers)
    assert watched.status_code == 201, watched.text
    assert len(client.get("/api/v1/watchlists", headers=headers).json()) == 1
    assert client.delete(f"/api/v1/watchlists/{supplier.json()['id']}", headers=headers).status_code == 204
    started = client.post(f"/api/v1/investigations/{investigation_id}/start", headers=headers)
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "completed"
    steps = client.get(f"/api/v1/investigations/{investigation_id}/steps", headers=headers)
    assert steps.status_code == 200
    assert [step["stage"] for step in steps.json()] == [
        "planning", "research", "extraction", "resolution", "verification",
        "graph", "risk", "recommendation", "report",
    ]
    assert steps.json()[1]["status"] == "skipped"
    assert client.post(f"/api/v1/investigations/{investigation_id}/pause", headers=headers).status_code == 409
    assert client.patch(f"/api/v1/investigations/{investigation_id}", headers=headers, json={"status": "archived"}).status_code == 200


def test_relationship_cannot_be_verified_without_evidence(client: TestClient):
    long_password = client.post(
        "/api/v1/auth/register",
        json={"email": "long@example.com", "password": "é" * 40, "full_name": "Long Password"},
    )
    assert long_password.status_code == 422
    token_response = client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "password": "SecurePass123", "full_name": "Second Analyst"},
    )
    headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
    supplier = client.post("/api/v1/entities", headers=headers, json={"name": "S", "entity_type": "supplier"})
    buyer = client.post("/api/v1/entities", headers=headers, json={"name": "B", "entity_type": "company"})
    relation = client.post("/api/v1/relationships", headers=headers, json={"source_entity_id": supplier.json()["id"], "target_entity_id": buyer.json()["id"], "relationship_type": "SUPPLIES"})
    result = client.post(f"/api/v1/relationships/{relation.json()['id']}/verify", headers=headers)
    assert result.status_code == 409


def test_investigation_and_evidence_are_private_to_the_owner(client: TestClient):
    owner = client.post("/api/v1/auth/register", json={
        "email": "owner@example.com", "password": "SecurePass123", "full_name": "Owner",
    })
    attacker = client.post("/api/v1/auth/register", json={
        "email": "attacker@example.com", "password": "SecurePass123", "full_name": "Attacker",
    })
    owner_headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
    attacker_headers = {"Authorization": f"Bearer {attacker.json()['access_token']}"}
    investigation = client.post("/api/v1/investigations", headers=owner_headers, json={"name": "Private investigation"})
    investigation_id = investigation.json()["id"]
    assert client.get(f"/api/v1/investigations/{investigation_id}", headers=attacker_headers).status_code == 404
    assert client.get(f"/api/v1/investigations/{investigation_id}/steps", headers=attacker_headers).status_code == 404

    source = client.post("/api/v1/sources", headers=attacker_headers, json={"name": "Private source", "source_type": "manual"})
    denied = client.post("/api/v1/evidence", headers=attacker_headers, json={
        "investigation_id": investigation_id,
        "source_id": source.json()["id"],
        "title": "Attempted access",
        "content": "Private evidence",
        "evidence_type": "manual",
    })
    assert denied.status_code == 404
