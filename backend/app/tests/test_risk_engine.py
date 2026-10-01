from collections.abc import Generator
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Alert, Base, Entity, Evidence, Investigation, Relationship, Risk, User, WatchlistEntry
from app.services.export_service import export_report
from app.services.report_service import generate_investigation_report
from app.services.risk_service import execute_risk_analysis
from risk_engine import EvidenceRecord, EntityRecord, RelationshipRecord, calculate_risk
from risk_engine.concentration import measured_hhi, structural_concentration
from risk_engine.common_dependency import detect_common_dependencies
from risk_engine.critical_dependency import _deepest_path
from risk_engine.risk_propagation import propagate_risk
from risk_engine.risk_scoring import make_factor, risk_level, weighted_score


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    with factory() as db:
        yield db
    engine.dispose()


def test_risk_scoring_is_bounded_and_unknown_factors_do_not_get_filled() -> None:
    unknown = make_factor("criticality", "Criticality", None, "No source-backed value.")
    known = make_factor("confidence", "Confidence risk", 125, "Clamped test input.")
    assert unknown.status == "UNKNOWN" and unknown.score is None
    assert known.score == 100
    assert weighted_score([unknown, known], {"criticality": 1, "confidence": 1}) == 100
    assert risk_level(None, (25, 50, 75)) == "UNKNOWN"
    assert [risk_level(value, (25, 50, 75)) for value in (0, 25, 50, 75)] == ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_concentration_requires_source_backed_shares_for_hhi() -> None:
    assert structural_concentration(1)[0] == 100
    assert structural_concentration(2)[0] == 50
    assert measured_hhi([{"metadata": {"share": 60}}, {"metadata": {"share": 40}}]) is None
    backed_shares = [
        {"metadata": {"share": 60, "share_source": "test fixture source A"}},
        {"metadata": {"share": 40, "share_evidence_ids": ["fixture-evidence-b"]}},
    ]
    assert measured_hhi(backed_shares) == 52
    assert measured_hhi([backed_shares[0], {"metadata": {}}]) is None


def test_propagation_is_directional_confidence_weighted_and_cycle_bounded() -> None:
    scores = propagate_risk(
        {"consumer": 10, "provider": 80, "other": None},
        [("consumer", "provider", 0.5), ("provider", "consumer", 1.0), ("other", "provider", None)],
        max_depth=3,
        decay=0.5,
    )
    assert scores["consumer"] == 20
    assert scores["provider"] == 80
    assert scores["other"] is None
    two_hops = propagate_risk(
        {"consumer": 0, "intermediate": 0, "provider": 100},
        [("consumer", "intermediate", 1.0), ("intermediate", "provider", 1.0)],
        max_depth=2,
        decay=0.5,
    )
    assert two_hops["intermediate"] == 50
    assert two_hops["consumer"] == 25


def test_common_dependency_detection_uses_distinct_verified_graph_consumers() -> None:
    patterns = detect_common_dependencies([
        {"source_id": "consumer-a", "target_id": "provider", "relationship_id": "rel-a"},
        {"source_id": "consumer-b", "target_id": "provider", "relationship_id": "rel-b"},
        {"source_id": "consumer-a", "target_id": "provider", "relationship_id": "rel-c"},
    ])
    assert len(patterns) == 1
    assert patterns[0]["type"] == "COMMON_DEPENDENCY"
    assert patterns[0]["related_entity_ids"] == ["consumer-a", "consumer-b"]
    assert len(patterns[0]["relationship_ids"]) == 3
    assert "does not establish spend share" in patterns[0]["explanation"]


def test_deep_dependency_path_uses_longest_dag_branch_and_respects_depth_cap() -> None:
    graph = {
        "root": ["short", "branch-a"],
        "short": ["join"],
        "branch-a": ["branch-b"],
        "branch-b": ["branch-c"],
        "branch-c": ["join"],
        "join": ["leaf"],
    }
    path = _deepest_path(graph, maximum_depth=6)
    assert path == ["root", "branch-a", "branch-b", "branch-c", "join", "leaf"]
    assert len(_deepest_path(graph, maximum_depth=3)) == 4


def test_high_concentration_requires_source_backed_shares_and_geography_uses_known_jurisdictions() -> None:
    from risk_engine.critical_dependency import detect_critical_dependencies

    entities = {
        "provider-a": {"entity_type": "supplier", "jurisdiction": "CN"},
        "provider-b": {"entity_type": "supplier", "jurisdiction": "CN"},
    }
    dependencies = [
        {"source_id": "consumer", "target_id": "provider-a", "relationship_id": "r-a", "metadata": {"share": 80}},
        {"source_id": "consumer", "target_id": "provider-b", "relationship_id": "r-b", "metadata": {"share": 20}},
    ]
    patterns = detect_critical_dependencies(entities, dependencies)
    assert {pattern["type"] for pattern in patterns} == {"GEOGRAPHIC_CONCENTRATION"}
    for edge, source in zip(dependencies, ("synthetic source A", "synthetic source B"), strict=True):
        edge["metadata"]["share_source"] = source
    backed = detect_critical_dependencies(entities, dependencies)
    assert {pattern["type"] for pattern in backed} == {"HIGH_CONCENTRATION", "GEOGRAPHIC_CONCENTRATION"}


def test_risk_engine_scores_only_verified_non_demo_dependencies_and_is_deterministic() -> None:
    entities = [
        EntityRecord("consumer", "Acme Electronics", "company", metadata={"criticality_score": 1, "criticality_score_source": "synthetic fixture source"}),
        EntityRecord("provider", "Battery Works", "supplier", jurisdiction="US"),
        EntityRecord("unknown", "Unresolved Source", "supplier"),
    ]
    relationships = [
        RelationshipRecord("verified", "provider", "consumer", "SUPPLIES", "VERIFIED", 0.8),
        RelationshipRecord("supported", "unknown", "consumer", "SUPPLIES", "SUPPORTED", 0.9),
        RelationshipRecord("demo", "unknown", "consumer", "SUPPLIES", "VERIFIED", 1.0, {"demo_only": True}),
    ]
    evidence = [EvidenceRecord("e1", "verified", "Registry filing", "official", date(2025, 1, 1))]
    as_of = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = calculate_risk(entities, relationships, evidence, target_name="Acme Electronics", as_of=as_of)
    second = calculate_risk(entities, relationships, evidence, target_name="Acme Electronics", as_of=as_of)

    assert first.as_dict() == second.as_dict()
    assert first.summary["verified_relationships_scored"] == 1
    assert first.summary["relationship_status_counts"] == {"SUPPORTED": 1, "VERIFIED": 2}
    assert all(0 <= risk.score <= 100 for risk in first.entity_risks if risk.score is not None)
    isolated = next(risk for risk in first.entity_risks if risk.target_id == "unknown")
    assert isolated.score == 0
    assert next(factor for factor in isolated.factors if factor.key == "dependency_depth").status == "UNKNOWN"
    no_graph_result = calculate_risk([entities[2]], [], [], as_of=as_of)
    assert no_graph_result.entity_risks[0].score is None
    assert any(item["type"] == "SINGLE_SOURCE" for item in first.critical_dependencies)


def test_risk_analysis_persists_snapshots_alerts_and_structured_exports(db_session: Session) -> None:
    user = User(email="risk-test@example.test", password_hash="test", full_name="Risk Tester")
    db_session.add(user)
    db_session.flush()
    investigation = Investigation(
        owner_id=user.id,
        name="Synthetic risk integration fixture",
        goal="Test deterministic scoring with explicitly synthetic records.",
        plan={"target": "Acme Electronics"},
        status="RISK_ANALYZING",
        progress=92,
        verification_progress={"finished_at": "2025-01-01T00:00:00+00:00"},
        demo_mode=False,
    )
    db_session.add(investigation)
    db_session.flush()
    consumer = Entity(
        investigation_id=investigation.id,
        name="Acme Electronics",
        entity_type="company",
        metadata_json={"criticality_score": 1.0, "criticality_score_source": "synthetic fixture source"},
    )
    provider = Entity(
        investigation_id=investigation.id,
        name="Battery Works",
        entity_type="supplier",
        jurisdiction="US",
    )
    db_session.add_all([consumer, provider])
    db_session.flush()
    relation = Relationship(
        investigation_id=investigation.id,
        source_entity_id=provider.id,
        target_entity_id=consumer.id,
        relationship_type="SUPPLIES",
        confidence=None,
        confidence_score=0.0,
        verification_status="VERIFIED",
        metadata_json={"verification": {"status": "VERIFIED", "supporting_evidence_ids": []}},
    )
    db_session.add(relation)
    db_session.flush()
    evidence = Evidence(
        investigation_id=investigation.id,
        relationship_id=relation.id,
        source="Example public registry",
        source_type="official_registry",
        source_url="https://registry.example.test/filing/1",
        published_date=date(2020, 1, 1),
        excerpt="Synthetic evidence record for an isolated test.",
        metadata_json={"synthetic_fixture": True},
    )
    db_session.add(evidence)
    db_session.flush()
    non_supporting_evidence = Evidence(
        investigation_id=investigation.id,
        relationship_id=relation.id,
        source="Unrelated newer record",
        source_type="news",
        published_date=date(2025, 12, 1),
        excerpt="This fixture is linked but was not classified as supporting evidence.",
        metadata_json={"synthetic_fixture": True},
    )
    db_session.add(non_supporting_evidence)
    relation.metadata_json = {
        **relation.metadata_json,
        "verification": {"status": "VERIFIED", "supporting_evidence_ids": [str(evidence.id)]},
    }
    watch = WatchlistEntry(
        owner_id=user.id,
        entity_id=consumer.id,
        investigation_id=investigation.id,
        target_type="entity",
        target_id=consumer.id,
        target_key=f"entity:{consumer.id}",
        risk_threshold=60,
        condition_json={"metric": "risk_score", "operator": "gte"},
    )
    db_session.add(watch)
    db_session.commit()

    completed = execute_risk_analysis(db_session, investigation.id, as_of=datetime(2026, 1, 1, tzinfo=timezone.utc))
    db_session.expire_all()
    stored_risks = db_session.scalars(select(Risk).where(Risk.investigation_id == investigation.id)).all()
    stored_alerts = db_session.scalars(select(Alert).where(Alert.investigation_id == investigation.id)).all()
    consumer_risk = next(row for row in stored_risks if row.entity_id == consumer.id and row.relationship_id is None)

    assert completed.status == "RISK_ANALYZED"
    assert completed.risk_progress["phase"] == "completed"
    assert consumer_risk.score_scale == "percent"
    assert consumer_risk.score is not None and 60 <= consumer_risk.score <= 100
    confidence_factor = next(factor for factor in consumer_risk.risk_factors if factor["key"] == "verification_confidence")
    freshness_factor = next(factor for factor in consumer_risk.risk_factors if factor["key"] == "evidence_freshness")
    assert confidence_factor["status"] == "UNKNOWN"
    assert freshness_factor["evidence_ids"] == [str(evidence.id)]
    assert {row.alert_type for row in stored_alerts} >= {
        "SINGLE_SOURCE_DEPENDENCY", "STALE_EVIDENCE", "WATCHLIST_CHANGE",
    }

    report = generate_investigation_report(db_session, completed, generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    json_export = export_report(report, "json")
    csv_export = export_report(report, "csv")
    assert '"demo_only": false' in json_export.content
    assert "Synthetic risk integration fixture" in csv_export.content
    assert "WATCHLIST_CHANGE" in csv_export.content
    assert report.structured_content["risk"]["record_count"] == len(stored_risks)
