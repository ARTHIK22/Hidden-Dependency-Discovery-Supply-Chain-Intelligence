from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import (
    AgentDecision,
    Alert,
    Base,
    Entity,
    Evidence,
    Investigation,
    InvestigationChange,
    MonitoringConfig,
    MonitoringRun,
    Relationship,
)
from app.services.monitoring_service import run_due_monitoring_once
from app.agents.monitoring.decision_engine import DetectedChange, decide_change, detect_changes


@pytest.fixture()
def monitoring_harness(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    def override_db() -> Generator[Session, None, None]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(settings, "jwt_secret_key", "monitoring-test-secret-with-at-least-32-bytes")
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "monitoring_scheduler_enabled", False)
    monkeypatch.setattr("app.services.monitoring_service.get_engine", lambda: engine)
    monkeypatch.setattr("app.api.v1.investigations.get_engine", lambda: engine)
    try:
        with TestClient(app) as client:
            yield client, factory
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def _register(client: TestClient, name: str) -> dict[str, str]:
    response = client.post("/api/auth/register", json={
        "full_name": name,
        "email": f"{name.casefold()}-{uuid4()}@example.test",
        "password": "monitoring-test-password-42",
    })
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_ready_investigation(
    client: TestClient,
    factory: sessionmaker[Session],
    headers: dict[str, str],
    *,
    depth: str = "deep",
) -> tuple[UUID, UUID]:
    response = client.post("/api/investigations", headers=headers, json={
        "goal": "Find upstream dependencies behind Acme Electronics for monitoring tests.",
        "depth": depth,
    })
    assert response.status_code == 201
    investigation_id = UUID(response.json()["investigation"]["id"])
    entity_id = uuid4()
    now = datetime.now(timezone.utc)
    with factory() as db:
        investigation = db.get(Investigation, investigation_id)
        assert investigation is not None
        investigation.status = "RISK_ANALYZED"
        investigation.research_mode = "external"
        investigation.research_progress = {"finished_at": now.isoformat(), "events": []}
        investigation.verification_mode = "deterministic"
        investigation.verification_progress = {"finished_at": now.isoformat(), "message": "Verified."}
        investigation.risk_analysis = {
            "snapshot_id": str(uuid4()), "entity_risks": [], "relationship_risks": [],
            "critical_dependencies": [], "summary": {},
        }
        db.add(Entity(
            id=entity_id, name="Acme Electronics", entity_type="COMPANY",
            investigation_id=investigation_id, metadata_json={}, identifiers=[],
        ))
        db.commit()
    return investigation_id, entity_id


def _add_verified_dependency(factory: sessionmaker[Session], investigation_id: UUID, consumer_id: UUID) -> tuple[UUID, UUID]:
    supplier_id = uuid4()
    relationship_id = uuid4()
    with factory() as db:
        supplier = Entity(
            id=supplier_id, name="Lithium Processor C", entity_type="COMPANY",
            investigation_id=investigation_id, metadata_json={}, identifiers=[],
        )
        relationship = Relationship(
            id=relationship_id, source_entity_id=supplier_id, target_entity_id=consumer_id,
            investigation_id=investigation_id, relationship_type="SUPPLIES", confidence=0.9,
            confidence_score=0.9, strength=0.9, verification_status="needs_review",
            metadata_json={},
        )
        db.add_all([supplier, relationship])
        db.flush()
        evidence_ids = []
        for index, domain in enumerate(("processor-registry.example.test", "buyer-disclosure.example.test")):
            evidence = Evidence(
                id=uuid4(), investigation_id=investigation_id, relationship_id=relationship_id,
                source=domain, source_type="test_fixture", source_url=f"https://{domain}/supplier/{index}",
                published_date=date.today(), captured_at=datetime.now(timezone.utc), confidence=0.9,
                verification_status="needs_review", excerpt="Lithium Processor C supplies Acme Electronics.",
                title="Deterministic monitoring fixture", content="Lithium Processor C supplies Acme Electronics.",
                evidence_type="source_statement", confidence_score=0.9,
                metadata_json={"relevance": 0.95, "source_domain": domain, "research_mode": "external"},
            )
            db.add(evidence)
            db.flush()
            evidence_ids.append(str(evidence.id))
        relationship.metadata_json = {"source_evidence_ids": evidence_ids, "research_mode": "external"}
        db.commit()
    return supplier_id, relationship_id


def test_monitoring_enable_no_change_decision_disable_and_scheduled_run(monitoring_harness) -> None:
    client, factory = monitoring_harness
    owner = _register(client, "MonitoringOwner")
    investigation_id, _ = _create_ready_investigation(client, factory, owner)

    enabled = client.post(f"/api/investigations/{investigation_id}/monitor", headers=owner, json={"interval_minutes": 15})
    assert enabled.status_code == 200
    assert enabled.json()["status"] == "MONITORING_ENABLED"
    assert enabled.json()["enabled"] is True
    assert enabled.json()["next_check_at"]

    response = client.post(f"/api/investigations/{investigation_id}/monitor/run", headers=owner, json={})
    assert response.status_code == 202
    state = client.get(f"/api/investigations/{investigation_id}/monitoring", headers=owner).json()
    assert state["status"] == "MONITORING_COMPLETED"
    assert state["last_run"]["status"] == "MONITORING_COMPLETED"
    decisions = client.get(f"/api/investigations/{investigation_id}/agent-decisions", headers=owner).json()["items"]
    assert decisions[0]["decision"] == "NO_ACTION"
    assert "No persisted graph" in decisions[0]["reason"]

    with factory() as db:
        config = db.get(MonitoringConfig, investigation_id)
        assert config is not None
        config.status = "MONITORING_ENABLED"
        config.next_check_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert run_due_monitoring_once() == 1
    assert client.get(f"/api/investigations/{investigation_id}/monitoring", headers=owner).json()["last_run"]["status"] == "MONITORING_COMPLETED"

    disabled = client.delete(f"/api/investigations/{investigation_id}/monitor", headers=owner)
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "MONITORING_DISABLED"
    assert disabled.json()["enabled"] is False


def test_persisted_graph_change_drives_research_reverification_alert_and_memory(monitoring_harness) -> None:
    client, factory = monitoring_harness
    owner = _register(client, "MonitoringGraphOwner")
    investigation_id, consumer_id = _create_ready_investigation(client, factory, owner, depth="deep")
    assert client.post(f"/api/investigations/{investigation_id}/monitor", headers=owner, json={"interval_minutes": 15}).status_code == 200
    supplier_id, relationship_id = _add_verified_dependency(factory, investigation_id, consumer_id)

    response = client.post(f"/api/investigations/{investigation_id}/monitor/run", headers=owner, json={})
    assert response.status_code == 202
    changes = client.get(f"/api/investigations/{investigation_id}/changes", headers=owner).json()["items"]
    change_types = {row["change_type"] for row in changes}
    assert {"NEW_ENTITY", "NEW_RELATIONSHIP", "NEW_UPSTREAM_DEPENDENCY", "EVIDENCE_CHANGED"} <= change_types
    decisions = client.get(f"/api/investigations/{investigation_id}/agent-decisions", headers=owner).json()["items"]
    followups = [row for row in decisions if row["decision"] == "RESEARCH_ENTITY" and row["entity_id"] == str(supplier_id)]
    followup = next(row for row in followups if row["followup_investigation_id"])
    assert followup["status"] == "COMPLETED"

    with factory() as db:
        child = db.get(Investigation, UUID(followup["followup_investigation_id"]))
        parent = db.get(Investigation, investigation_id)
        children = [row for row in db.scalars(select(Investigation)).all() if (row.autonomous_context or {}).get("parent_investigation_id") == str(investigation_id)]
        assert len(children) == 1
        assert child is not None and child.status == "RISK_ANALYZED"
        assert child.autonomous_context["parent_investigation_id"] == str(investigation_id)
        child_monitor = db.get(MonitoringConfig, child.id)
        assert child_monitor is not None and child_monitor.enabled is True
        assert child_monitor.interval_minutes == 15
        assert child_monitor.max_autonomous_depth == 2
        assert str(supplier_id) in child_monitor.memory_json["visited_entity_ids"]
        assert child_monitor.memory_json["executed_query_hashes"]
        assert parent is not None and parent.status == "RISK_ANALYZED"
        memory = db.get(MonitoringConfig, investigation_id).memory_json
        assert str(supplier_id) in memory["visited_entity_ids"]
        assert memory["executed_query_hashes"]
        assert db.scalar(select(AgentDecision.id).where(
            AgentDecision.investigation_id == investigation_id,
            AgentDecision.relationship_id == relationship_id,
            AgentDecision.decision == "REVERIFY_RELATIONSHIP",
        )) is not None
        assert db.scalar(select(MonitoringRun.id).where(MonitoringRun.investigation_id == investigation_id, MonitoringRun.status == "MONITORING_COMPLETED")) is not None
        assert db.scalar(select(InvestigationChange.id).where(InvestigationChange.investigation_id == investigation_id)) is not None

    alerts = client.get("/api/alerts", headers=owner).json()["items"]
    assert any(row["alert_type"] == "NEW_UPSTREAM_DEPENDENCY" and row["relationship_id"] == str(relationship_id) for row in alerts)
    detail = client.get(f"/api/investigations/{investigation_id}", headers=owner).json()
    event_types = {item["type"] for item in detail["timeline"]}
    assert {"monitoring_started", "change_detected", "agent_decision", "followup_started", "followup_completed", "monitoring_completed"} <= event_types

    count_before = len(changes)
    client.post(f"/api/investigations/{investigation_id}/monitor/run", headers=owner, json={})
    changes_after = client.get(f"/api/investigations/{investigation_id}/changes", headers=owner).json()["items"]
    assert len(changes_after) == count_before
    with factory() as db:
        assert db.scalar(select(Alert.id).where(Alert.investigation_id == investigation_id, Alert.alert_type == "NEW_UPSTREAM_DEPENDENCY")) is not None


def test_stale_supporting_evidence_conflict_and_risk_delta_are_detected(monitoring_harness) -> None:
    client, factory = monitoring_harness
    owner = _register(client, "MonitoringEvidenceOwner")
    investigation_id, consumer_id = _create_ready_investigation(client, factory, owner)
    supplier_id, relationship_id = _add_verified_dependency(factory, investigation_id, consumer_id)
    with factory() as db:
        relationship = db.get(Relationship, relationship_id)
        evidence = db.scalars(select(Evidence).where(Evidence.relationship_id == relationship_id)).all()
        assert relationship is not None
        evidence_ids = [str(row.id) for row in evidence]
        relationship.verification_status = "VERIFIED"
        relationship.metadata_json = {
            "source_evidence_ids": evidence_ids,
            "verification": {"supporting_evidence_ids": evidence_ids, "status": "VERIFIED"},
        }
        for row in evidence:
            row.published_date = date.today()
        db.commit()
    assert client.post(f"/api/investigations/{investigation_id}/monitor", headers=owner, json={"interval_minutes": 15}).status_code == 200

    with factory() as db:
        evidence = db.scalars(select(Evidence).where(Evidence.relationship_id == relationship_id)).all()
        for row in evidence:
            row.published_date = date.today() - timedelta(days=settings.monitoring_evidence_freshness_days + 1)
        relationship = db.get(Relationship, relationship_id)
        assert relationship is not None
        relationship.verification_status = "CONFLICTED"
        db.commit()
    client.post(f"/api/investigations/{investigation_id}/monitor/run", headers=owner, json={})
    changes = client.get(f"/api/investigations/{investigation_id}/changes", headers=owner).json()["items"]
    change_types = {row["change_type"] for row in changes}
    assert {"RELATIONSHIP_CHANGED", "VERIFICATION_CONFLICT", "EVIDENCE_CHANGED", "EVIDENCE_BECAME_STALE"} <= change_types
    decisions = client.get(f"/api/investigations/{investigation_id}/agent-decisions", headers=owner).json()["items"]
    assert any(row["decision"] == "REQUEST_HUMAN_REVIEW" and row["trigger_event"] == "VERIFICATION_CONFLICT" for row in decisions)
    with factory() as db:
        assert db.scalar(select(Alert.id).where(Alert.investigation_id == investigation_id, Alert.alert_type == "STALE_EVIDENCE")) is not None
        assert str(supplier_id) in db.get(MonitoringConfig, investigation_id).memory_json["visited_entity_ids"]


def test_monitoring_and_history_routes_enforce_owner_scope_and_read_auth(monitoring_harness) -> None:
    client, factory = monitoring_harness
    owner = _register(client, "MonitoringRouteOwner")
    outsider = _register(client, "MonitoringRouteOutsider")
    investigation_id, _ = _create_ready_investigation(client, factory, owner)
    assert client.get(f"/api/investigations/{investigation_id}/monitoring").status_code == 401
    assert client.post(f"/api/investigations/{investigation_id}/monitor", headers=outsider, json={}).status_code == 404
    assert client.delete(f"/api/investigations/{investigation_id}/monitor", headers=outsider).status_code == 404
    assert client.post(f"/api/investigations/{investigation_id}/monitor/run", headers=outsider, json={}).status_code == 404
    assert client.get(f"/api/investigations/{investigation_id}/changes", headers=outsider).status_code == 404
    assert client.get(f"/api/investigations/{investigation_id}/agent-decisions", headers=outsider).status_code == 404


def test_disabling_monitoring_during_a_run_returns_conflict(monitoring_harness) -> None:
    client, factory = monitoring_harness
    owner = _register(client, "MonitoringDisableOwner")
    investigation_id, _ = _create_ready_investigation(client, factory, owner)
    assert client.post(f"/api/investigations/{investigation_id}/monitor", headers=owner, json={}).status_code == 200
    with factory() as db:
        config = db.get(MonitoringConfig, investigation_id)
        assert config is not None
        config.status = "MONITORING_RUNNING"
        config.run_started_at = datetime.now(timezone.utc)
        db.commit()

    response = client.delete(f"/api/investigations/{investigation_id}/monitor", headers=owner)
    assert response.status_code == 409
    assert client.get(f"/api/investigations/{investigation_id}/monitoring", headers=owner).json()["enabled"] is True


def test_monitoring_rejects_unverified_and_demo_investigations(monitoring_harness) -> None:
    client, factory = monitoring_harness
    owner = _register(client, "MonitoringGateOwner")
    response = client.post("/api/investigations", headers=owner, json={
        "goal": "Find upstream dependencies behind Acme Electronics for gating tests.",
        "depth": "standard",
    })
    investigation_id = response.json()["investigation"]["id"]
    assert client.post(f"/api/investigations/{investigation_id}/monitor", headers=owner, json={}).status_code == 409
    with factory() as db:
        demo = db.scalar(select(Investigation).where(Investigation.demo_mode.is_(True)))
        if demo is None:
            demo = Investigation(name="Fictional demo", goal="Fictional demo scenario", scope={}, depth="standard", demo_mode=True, status="VERIFICATION_COMPLETED", plan={"target": "Example"}, verification_progress={"finished_at": datetime.now(timezone.utc).isoformat()})
            db.add(demo)
            db.commit()
        demo_id = demo.id
        owner_id = UUID(client.get("/api/auth/me", headers=owner).json()["id"])
        demo.owner_id = owner_id
        db.commit()
    assert client.post(f"/api/investigations/{demo_id}/monitor", headers=owner, json={}).status_code == 409


def test_standard_depth_records_limit_and_does_not_create_child(monitoring_harness) -> None:
    client, factory = monitoring_harness
    owner = _register(client, "MonitoringDepthOwner")
    investigation_id, consumer_id = _create_ready_investigation(client, factory, owner, depth="standard")
    with factory() as db:
        investigation = db.get(Investigation, investigation_id)
        assert investigation is not None
        investigation.autonomous_context = {"autonomous_depth": 1, "maximum_autonomous_depth": 1}
        db.commit()
    assert client.post(f"/api/investigations/{investigation_id}/monitor", headers=owner, json={}).status_code == 200
    supplier_id, _ = _add_verified_dependency(factory, investigation_id, consumer_id)
    client.post(f"/api/investigations/{investigation_id}/monitor/run", headers=owner, json={})
    changes = client.get(f"/api/investigations/{investigation_id}/changes", headers=owner).json()["items"]
    assert any(item["change_type"] == "AUTONOMOUS_DEPTH_LIMIT_REACHED" for item in changes)
    decisions = client.get(f"/api/investigations/{investigation_id}/agent-decisions", headers=owner).json()["items"]
    assert any(item["decision"] == "REQUEST_HUMAN_REVIEW" and item["entity_id"] == str(supplier_id) for item in decisions)
    assert not any(item["followup_investigation_id"] for item in decisions)


def test_decision_engine_detects_significant_risk_deltas_and_enforces_memory() -> None:
    previous = {
        "entities": {"consumer": {"name": "Acme"}},
        "relationships": {}, "evidence": {}, "stale_evidence_ids": [],
        "risk_scores": {"consumer": 40.0}, "critical_dependencies": {},
        "watchlist_targets": [], "alert_state": [],
    }
    current = {**previous, "risk_scores": {"consumer": 55.0}}
    changes = detect_changes(previous, current)
    assert [change.change_type for change in changes] == ["RISK_INCREASED"]
    change = changes[0]
    decision, reason, priority = decide_change(
        change, watched_target_ids={"consumer"}, visited_entity_ids={"consumer"}, depth_available=False,
    )
    assert decision == "RECALCULATE_RISK"
    assert "increased from 40 to 55/100" in reason
    assert priority == "high"

    added_risk = detect_changes(
        {**previous, "risk_scores": {}},
        {**previous, "risk_scores": {"consumer": 42.0}},
    )
    assert added_risk[0].change_type == "RISK_ASSESSMENT_ADDED"
    removed_risk = detect_changes(
        previous,
        {**previous, "risk_scores": {}},
    )
    assert removed_risk[0].change_type == "RISK_ASSESSMENT_REMOVED"

    new_entity = DetectedChange("NEW_ENTITY", "entity:new", entity_id="new")
    decision, reason, _ = decide_change(
        new_entity, watched_target_ids=set(), visited_entity_ids={"new"}, depth_available=True,
    )
    assert decision == "NO_ACTION"
    assert "already present in investigation memory" in reason
    decision, _, _ = decide_change(
        new_entity, watched_target_ids=set(), visited_entity_ids=set(), depth_available=False,
    )
    assert decision == "REQUEST_HUMAN_REVIEW"


def test_monitoring_websocket_is_owner_scoped_and_streams_agent_events(monitoring_harness) -> None:
    client, factory = monitoring_harness
    owner = _register(client, "MonitoringSocketOwner")
    outsider = _register(client, "MonitoringSocketOutsider")
    investigation_id, _ = _create_ready_investigation(client, factory, owner)
    assert client.post(f"/api/investigations/{investigation_id}/monitor", headers=owner, json={}).status_code == 200
    token = owner["Authorization"].split(" ", 1)[1]
    outsider_token = outsider["Authorization"].split(" ", 1)[1]
    from starlette.websockets import WebSocketDisconnect

    with client.websocket_connect(
        f"/ws/investigations/{investigation_id}", subprotocols=["hdi", f"bearer.{outsider_token}"]
    ) as websocket:
        assert websocket.receive_json()["type"] == "error"
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()

    with client.websocket_connect(
        f"/ws/investigations/{investigation_id}", subprotocols=["hdi", f"bearer.{token}"]
    ) as websocket:
        initial = websocket.receive_json()
        assert initial["type"] in {"risk_progress", "snapshot"}
        client.post(f"/api/investigations/{investigation_id}/monitor/run", headers=owner, json={})
        seen = set()
        for _ in range(8):
            message = websocket.receive_json()
            seen.add(message["type"])
            if "agent_decision" in seen and "monitoring_completed" in seen:
                break
        assert {"monitoring_started", "agent_decision", "monitoring_completed"} <= seen


def test_websocket_stops_before_sending_after_investigation_changes_owner(monitoring_harness) -> None:
    client, factory = monitoring_harness
    owner = _register(client, "SocketTransferOwner")
    new_owner = _register(client, "SocketTransferNewOwner")
    investigation_id, _ = _create_ready_investigation(client, factory, owner)
    owner_id = UUID(client.get("/api/auth/me", headers=new_owner).json()["id"])
    token = owner["Authorization"].split(" ", 1)[1]

    from starlette.websockets import WebSocketDisconnect

    with client.websocket_connect(
        f"/ws/investigations/{investigation_id}", subprotocols=["hdi", f"bearer.{token}"]
    ) as websocket:
        initial = websocket.receive_json()
        assert initial["investigation_id"] == str(investigation_id)
        with factory() as db:
            investigation = db.get(Investigation, investigation_id)
            assert investigation is not None
            investigation.owner_id = owner_id
            db.commit()
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()
