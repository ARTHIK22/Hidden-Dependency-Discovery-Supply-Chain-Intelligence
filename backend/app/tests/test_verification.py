from collections.abc import Generator
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.entity_resolution import normalize_name, resolve_entities
from app.agents.verification import verify_relationship
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import Base, Entity, Evidence, Investigation, Relationship
from app.services.verification_service import execute_verification, start_verification


@pytest.fixture()
def verify_harness(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(settings, "jwt_secret_key", "verification-test-secret-with-at-least-32-bytes")
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr("app.api.v1.investigations.get_engine", lambda: engine)
    app.state.research_test_session_factory = factory
    try:
        with TestClient(app) as client:
            yield client, factory
    finally:
        app.dependency_overrides.clear()
        del app.state.research_test_session_factory
        engine.dispose()


def _auth(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/register", json={
        "full_name": "Verification Tester", "email": f"{uuid4()}@example.test", "password": "verification-test-password"
    })
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _new_investigation(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/api/investigations", headers=headers, json={
        "goal": "Find supplier dependencies for Acme Electronics", "depth": "deep"
    })
    assert response.status_code == 201
    return response.json()["investigation"]["id"]


def _mark_research_complete(factory: sessionmaker[Session], investigation_id: str) -> None:
    with factory() as db:
        investigation = db.get(Investigation, UUID(investigation_id))
        assert investigation is not None
        investigation.status = "COMPLETED"
        investigation.research_progress = {"finished_at": datetime.now(timezone.utc).isoformat(), "mode": "external"}
        db.commit()


def _add_relationship(factory: sessionmaker[Session], investigation_id: str, *, evidence_texts: list[tuple[str, str]] | None = None) -> UUID:
    with factory() as db:
        investigation = db.get(Investigation, UUID(investigation_id))
        assert investigation is not None
        source = Entity(name="Supplier B", entity_type="COMPANY", investigation_id=investigation.id, metadata_json={})
        target = Entity(name="Acme Electronics", entity_type="COMPANY", investigation_id=investigation.id, metadata_json={})
        db.add_all([source, target])
        db.flush()
        relation = Relationship(
            source_entity_id=source.id, target_entity_id=target.id, investigation_id=investigation.id,
            relationship_type="SUPPLIES", confidence=0.8, verification_status="needs_review", metadata_json={}
        )
        db.add(relation)
        db.flush()
        for index, (domain, text) in enumerate(evidence_texts or []):
            db.add(Evidence(
                investigation_id=investigation.id, relationship_id=relation.id,
                source=domain, source_type="test_fixture", source_url=f"https://{domain}/disclosure/{index}",
                title="Supplier disclosure", excerpt=text, content=text, captured_at=datetime.now(timezone.utc),
                confidence=0.8, verification_status="needs_review", metadata_json={"relevance": 0.8, "source_domain": domain},
            ))
        db.commit()
        return relation.id


def test_normalization_candidates_type_guard_and_contextual_alias() -> None:
    assert normalize_name("Apple Incorporated") == normalize_name("APPLE INC") == "apple"
    a = SimpleNamespace(id="a", name="Apple Inc.", entity_type="COMPANY", identifiers=[], metadata_json={}, description=None, jurisdiction=None, created_at="1")
    b = SimpleNamespace(id="b", name="Apple Incorporated", entity_type="COMPANY", identifiers=[], metadata_json={}, description=None, jurisdiction=None, created_at="2")
    product = SimpleNamespace(id="c", name="Apple", entity_type="PRODUCT", identifiers=[], metadata_json={}, description=None, jurisdiction=None, created_at="3")
    results = resolve_entities([a, b, product])
    assert results["a"].match_type == results["b"].match_type == "POSSIBLE_DUPLICATE"
    assert results["a"].canonical_entity_id is None
    assert results["c"].canonical_entity_id == "c"
    b.identifiers = ["Apple Inc."]
    merged = resolve_entities([a, b], target_name="Apple Inc.")
    assert merged["a"].canonical_entity_id == merged["b"].canonical_entity_id == "b"
    assert merged["a"].match_type == "ALIAS"


def test_verification_rules_require_direct_evidence_and_corrobate_sources() -> None:
    relation = SimpleNamespace(id="r", relationship_type="SUPPLIES", confidence=0.8, confidence_score=0.8)
    supplier = SimpleNamespace(id="a", name="Supplier B", identifiers=[], metadata_json={})
    customer = SimpleNamespace(id="b", name="Acme Electronics", identifiers=[], metadata_json={})

    def evidence(identity: str, domain: str, text: str):
        return SimpleNamespace(
            id=identity, title="Disclosure", excerpt=text, content=text, source_url=f"https://{domain}/page",
            source=domain, metadata_json={"relevance": 0.8}, confidence=0.8, published_date=None,
            captured_at=datetime.now(timezone.utc),
        )

    empty = verify_relationship(relation, supplier, customer, [])
    assert empty.status == "INSUFFICIENT_EVIDENCE" and empty.confidence == 0
    one = verify_relationship(relation, supplier, customer, [evidence("e1", "a.test", "Supplier B supplies Acme Electronics.")])
    assert one.status == "SUPPORTED"
    several = verify_relationship(relation, supplier, customer, [
        evidence("e1", "a.test", "Supplier B supplies Acme Electronics."),
        evidence("e2", "b.test", "Supplier B supplies Acme Electronics."),
        evidence("e3", "c.test", "Supplier B supplies Acme Electronics."),
    ])
    assert several.status == "VERIFIED"
    assert several.confidence > one.confidence
    conflict = verify_relationship(relation, supplier, customer, [
        evidence("e1", "a.test", "Supplier B supplies Acme Electronics."),
        evidence("e2", "b.test", "Supplier B no longer supplies Acme Electronics."),
    ])
    assert conflict.status == "CONFLICTED"
    assert conflict.supporting_evidence == ("e1",)
    assert conflict.conflicting_evidence == ("e2",)


def test_verification_api_requires_owner_and_valid_phase(verify_harness, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _factory = verify_harness
    owner, other = _auth(client), _auth(client)
    investigation_id = _new_investigation(client, owner)
    assert client.post(f"/api/investigations/{investigation_id}/verify").status_code == 401
    assert client.post(f"/api/investigations/{investigation_id}/verify", headers=owner).status_code == 409
    assert client.get(f"/api/investigations/{investigation_id}/verification", headers=other).status_code == 404
    assert client.get(f"/api/investigations/{investigation_id}", headers=other).status_code == 404


def test_start_verification_persists_verifying_state_and_websocket_event(verify_harness, monkeypatch: pytest.MonkeyPatch) -> None:
    client, factory = verify_harness
    headers, other = _auth(client), _auth(client)
    investigation_id = _new_investigation(client, headers)
    _mark_research_complete(factory, investigation_id)
    monkeypatch.setattr("app.api.v1.investigations.run_verification_background", lambda _id: None)
    response = client.post(f"/api/investigations/{investigation_id}/verify", headers=headers)
    assert response.status_code == 202
    assert response.json()["status"] == "VERIFYING"
    token = headers["Authorization"].split(" ", 1)[1]
    other_token = other["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/ws/investigations/{investigation_id}", subprotocols=["hdi", f"bearer.{other_token}"]) as websocket:
        assert websocket.receive_json()["type"] == "error"
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()
    with client.websocket_connect(f"/ws/investigations/{investigation_id}", subprotocols=["hdi", f"bearer.{token}"]) as websocket:
        event = websocket.receive_json()
        assert event["type"] == "verification_progress"
        assert event["status"] == "VERIFYING"
        assert event["verification"]["resolution_mode"] == "deterministic"


def test_verification_persists_supported_verified_and_insufficient_states(verify_harness) -> None:
    client, factory = verify_harness
    headers = _auth(client)
    investigation_id = _new_investigation(client, headers)
    _mark_research_complete(factory, investigation_id)
    _add_relationship(factory, investigation_id, evidence_texts=[("one.test", "Supplier B supplies Acme Electronics.")])
    _add_relationship(factory, investigation_id, evidence_texts=[
        ("two.test", "Supplier B supplies Acme Electronics."), ("three.test", "Supplier B supplies Acme Electronics.")
    ])
    _add_relationship(factory, investigation_id)
    with factory() as db:
        start_verification(db, UUID(investigation_id))
        completed = execute_verification(db, UUID(investigation_id))
        assert completed.status == "VERIFICATION_COMPLETED"
        assert completed.verification_mode == "deterministic"
        rows = db.scalars(select(Relationship).where(Relationship.investigation_id == UUID(investigation_id))).all()
        assert sorted(row.verification_status for row in rows) == ["INSUFFICIENT_EVIDENCE", "SUPPORTED", "VERIFIED"]
        verified = next(row for row in rows if row.verification_status == "VERIFIED")
        assert verified.metadata_json["verification"]["verified_at"]
        assert len(verified.metadata_json["verification"]["supporting_evidence_ids"]) == 2
        assert completed.verification_progress["verified_relationships"] == 1


def test_verification_preserves_conflicts_and_reports_failure(verify_harness, monkeypatch: pytest.MonkeyPatch) -> None:
    client, factory = verify_harness
    headers = _auth(client)
    investigation_id = _new_investigation(client, headers)
    _mark_research_complete(factory, investigation_id)
    _add_relationship(factory, investigation_id, evidence_texts=[
        ("yes.test", "Supplier B supplies Acme Electronics."),
        ("no.test", "Supplier B no longer supplies Acme Electronics."),
    ])
    with factory() as db:
        start_verification(db, UUID(investigation_id))
        completed = execute_verification(db, UUID(investigation_id))
        relation = db.scalar(select(Relationship).where(Relationship.investigation_id == UUID(investigation_id)))
        assert completed.status == "VERIFICATION_COMPLETED"
        assert relation is not None and relation.verification_status == "CONFLICTED"
        assert len(relation.metadata_json["verification"]["supporting_evidence_ids"]) == 1
        assert len(relation.metadata_json["verification"]["conflicting_evidence_ids"]) == 1

    failure_id = _new_investigation(client, headers)
    _mark_research_complete(factory, failure_id)
    monkeypatch.setattr("app.services.verification_service.resolve_entities", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fixture error")))
    with factory() as db:
        start_verification(db, UUID(failure_id))
        with pytest.raises(Exception):
            execute_verification(db, UUID(failure_id))
        failed = db.get(Investigation, UUID(failure_id))
        assert failed is not None and failed.status == "FAILED"
        assert failed.error_message == "Verification could not be completed."


def test_alias_relationship_candidates_aggregate_evidence_into_one_graph_edge(verify_harness) -> None:
    client, factory = verify_harness
    headers = _auth(client)
    investigation_id = _new_investigation(client, headers)
    _mark_research_complete(factory, investigation_id)
    with factory() as db:
        investigation = db.get(Investigation, UUID(investigation_id))
        assert investigation is not None
        first = Entity(name="Apple Inc.", entity_type="COMPANY", investigation_id=investigation.id, metadata_json={"aliases": ["Apple Incorporated"]})
        second = Entity(name="Apple Incorporated", entity_type="COMPANY", investigation_id=investigation.id, metadata_json={"aliases": ["Apple Inc."]})
        customer = Entity(name="Acme Electronics", entity_type="COMPANY", investigation_id=investigation.id, metadata_json={})
        db.add_all([first, second, customer])
        db.flush()
        relations = [
            Relationship(source_entity_id=entity.id, target_entity_id=customer.id, investigation_id=investigation.id, relationship_type="SUPPLIES", confidence=0.8, verification_status="needs_review", metadata_json={})
            for entity in (first, second)
        ]
        db.add_all(relations)
        db.flush()
        db.add_all([
            Evidence(
                investigation_id=investigation.id, relationship_id=relations[0].id, source="one.test", source_type="fixture",
                source_url="https://one.test/disclosure", title="Supplier disclosure", excerpt="Apple Inc. supplies Acme Electronics.",
                content="Apple Inc. supplies Acme Electronics.", captured_at=datetime.now(timezone.utc), confidence=0.8,
                verification_status="needs_review", metadata_json={"relevance": 0.8},
            ),
            Evidence(
                investigation_id=investigation.id, relationship_id=relations[1].id, source="two.test", source_type="fixture",
                source_url="https://two.test/disclosure", title="Supplier disclosure", excerpt="Apple Incorporated supplies Acme Electronics.",
                content="Apple Incorporated supplies Acme Electronics.", captured_at=datetime.now(timezone.utc), confidence=0.8,
                verification_status="needs_review", metadata_json={"relevance": 0.8},
            ),
        ])
        db.commit()
        start_verification(db, investigation.id)
        completed = execute_verification(db, investigation.id)
        persisted = db.scalars(select(Relationship).where(Relationship.investigation_id == investigation.id)).all()
        assert completed.status == "VERIFICATION_COMPLETED"
        assert completed.verification_progress["total_relationships"] == 1
        assert completed.verification_progress["relationship_candidates"] == 2
        assert all(row.verification_status == "VERIFIED" for row in persisted), [
            (row.verification_status, row.metadata_json["verification"]["independent_source_domains"],
             row.metadata_json["verification"]["evidence_scores"], row.metadata_json["verification"]["supporting_evidence_ids"])
            for row in persisted
        ]
        assert all(len(row.metadata_json["verification"]["evidence_ids"]) == 2 for row in persisted)

    graph = client.get("/api/graph", headers=headers).json()
    edges = [edge for edge in graph["edges"] if edge["data"].get("relationshipType") == "SUPPLIES"]
    assert len(edges) == 1
    assert edges[0]["data"]["verificationStatus"] == "VERIFIED"
    assert len(edges[0]["data"]["evidenceItems"]) == 2
