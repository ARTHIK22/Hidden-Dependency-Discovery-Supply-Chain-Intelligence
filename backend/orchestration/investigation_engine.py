import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.audit_log import AuditLog
from app.models.entity import Entity
from app.models.entity_alias import EntityAlias
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.investigation_step import InvestigationStep
from app.models.relationship import Relationship
from app.models.report import Report
from app.models.source import Source
from sqlalchemy import func
from extraction.relationship_extractor import extract_relationship_candidates
from graph.graph_builder import build_graph
from risk_engine.risk_engine import analyze_risks
from verification.relationship_verifier import verify_relationship_claim
from orchestration.decision_engine import research_decision

logger = get_logger(__name__)
STAGES = ("planning", "research", "extraction", "resolution", "verification", "graph", "risk", "recommendation", "report")


def run_investigation(db: Session, investigation: Investigation) -> dict:
    """Run bounded, database-only analysis. It never invents facts or fetches external data."""
    investigation.status = "running"
    start_sequence = (db.scalar(select(func.max(InvestigationStep.sequence)).where(
        InvestigationStep.investigation_id == investigation.id
    )) or 0)
    evidence = list(db.scalars(select(Evidence).where(Evidence.investigation_id == investigation.id).order_by(Evidence.collected_at)))
    entities = list(db.scalars(select(Entity)))
    aliases = list(db.scalars(select(EntityAlias)))
    source_ids = {item.source_id for item in evidence if item.source_id}
    sources = {source.id: source for source in db.scalars(select(Source).where(Source.id.in_(source_ids)))} if source_ids else {}
    relationships_by_id = {}
    linked_ids = {item.relationship_id for item in evidence if item.relationship_id}
    if linked_ids:
        relationships_by_id = {item.id: item for item in db.scalars(select(Relationship).where(Relationship.id.in_(linked_ids)))}
    alias_names: dict[str, list[str]] = {}
    entity_by_name: dict[str, Entity] = {}
    for entity in entities:
        entity_by_name[entity.name.casefold()] = entity
        entity_by_name[(entity.canonical_name or entity.name).casefold()] = entity
    for alias in aliases:
        alias_names.setdefault(str(alias.entity_id), []).append(alias.alias)
        entity = next((candidate for candidate in entities if candidate.id == alias.entity_id), None)
        if entity is not None:
            entity_by_name[alias.alias.casefold()] = entity

    candidates: list[dict] = []
    step_outputs: dict[str, dict] = {}
    current_stage = "planning"
    try:
        planning = {"target": investigation.target, "description": investigation.description, "scope": "stored investigation evidence and linked relationships"}
        step_outputs["planning"] = planning
        current_stage = "research"
        step_outputs["research"] = {**research_decision(configured_connectors=[], stored_evidence_count=len(evidence)), "external_access_performed": False}
        current_stage = "extraction"
        for item in evidence:
            extracted = extract_relationship_candidates(item.content, list(entity_by_name))
            for candidate in extracted:
                source_entity = entity_by_name.get(candidate["source_name"].casefold())
                target_entity = entity_by_name.get(candidate["target_name"].casefold())
                candidates.append({**candidate, "evidence_id": str(item.id), "source_entity_id": str(source_entity.id) if source_entity else None, "target_entity_id": str(target_entity.id) if target_entity else None})
        step_outputs["extraction"] = {"evidence_processed": len(evidence), "relationship_candidates": candidates, "facts_persisted": False}
        current_stage = "resolution"
        step_outputs["resolution"] = {"matched_candidates": sum(bool(item["source_entity_id"] and item["target_entity_id"]) for item in candidates), "unresolved_candidates": sum(not (item["source_entity_id"] and item["target_entity_id"]) for item in candidates), "auto_merge": False}
        current_stage = "verification"
        verification_results = []
        for relationship_id, relationship in relationships_by_id.items():
            evidence_items = [item for item in evidence if item.relationship_id == relationship_id]
            verification_results.append({"relationship_id": str(relationship_id), **verify_relationship_claim(evidence_items, sources)})
        step_outputs["verification"] = {"claims_checked": len(verification_results), "results": verification_results, "database_claims_changed": False}
        current_stage = "graph"
        graph = build_graph(list(relationships_by_id.values()))
        step_outputs["graph"] = {"node_count": len({node for edge in graph.edges for node in (edge.source, edge.target)}), "edge_count": len(graph.edges), "relationship_ids": [str(identity) for identity in relationships_by_id]}
        current_stage = "risk"
        analysis = analyze_risks(graph)
        step_outputs["risk"] = analysis
        current_stage = "recommendation"
        recommendations = []
        for risk in analysis["risks"]:
            if risk["category"] in {"common_dependency", "supplier_concentration", "single_point_of_failure"}:
                recommendations.append({"recommendation": "Review alternative supplier options and validate the recorded dependency with independent evidence.", "basis": risk["category"], "entity_id": risk.get("entity_id")})
        step_outputs["recommendation"] = {"recommendations": recommendations, "generated_from": "recorded relationship structure"}
        current_stage = "report"
        from app.services.report_service import build_report
        report_data = build_report(db, investigation)
        report_data["analysis"] = {"risk_signals": analysis["risks"], "recommendations": recommendations, "workflow_scope": "stored evidence only"}
        report = Report(investigation_id=investigation.id, title=f"Investigation report: {investigation.name}", report_type="json", content=json.dumps(report_data, ensure_ascii=False), status="generated")
        db.add(report)
        db.flush()
        step_outputs["report"] = {"report_id": str(report.id), "evidence_count": len(evidence), "external_research_used": False}

        now = datetime.now(timezone.utc)
        for sequence, stage in enumerate(STAGES, start=start_sequence + 1):
            skipped = stage == "research"
            db.add(InvestigationStep(
                investigation_id=investigation.id,
                sequence=sequence,
                stage=stage,
                status="skipped" if skipped else "completed",
                input_data={"evidence_count": len(evidence)} if stage != "planning" else {"target": investigation.target},
                output_data=step_outputs[stage],
                started_at=now,
                completed_at=now,
            ))
        investigation.status = "completed"
        db.add(AuditLog(user_id=investigation.created_by, action="investigation_completed", resource_type="investigation", resource_id=str(investigation.id), metadata_json={"scope": "stored evidence only", "report_id": str(report.id)}))
        db.commit()
        return {"status": investigation.status, "scope": "stored evidence only", "steps": [{"stage": stage, "status": "skipped" if stage == "research" else "completed", "output": step_outputs[stage]} for stage in STAGES], "report_id": str(report.id)}
    except Exception as exc:
        logger.exception("Investigation %s failed during local analysis", investigation.id)
        db.rollback()
        investigation = db.get(Investigation, investigation.id)
        if investigation is None:
            raise
        now = datetime.now(timezone.utc)
        sequence = start_sequence + len(step_outputs) + 1
        db.add(InvestigationStep(investigation_id=investigation.id, sequence=sequence, stage=current_stage, status="failed", input_data={}, output_data={}, error_message=str(exc), started_at=now, completed_at=now))
        investigation.status = "failed"
        db.commit()
        return {"status": "failed", "scope": "stored evidence only", "failed_stage": STAGES[min(sequence - 1, MAX_WORKFLOW_STEPS - 1)], "error": "See investigation timeline for failure details"}
