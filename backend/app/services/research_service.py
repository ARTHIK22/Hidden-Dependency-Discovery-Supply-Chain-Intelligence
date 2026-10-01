import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.research import ResearchAgent
from app.agents.schemas import InvestigationPlan
from app.core.database import get_engine
from app.models import Entity, Evidence, Investigation, Relationship
from app.research.models import ExtractedEntity, ResearchBatch, ResearchQuery, ResearchResult
from app.research.provider import ResearchProvider, UnconfiguredResearchProvider, validate_fetch_url


logger = logging.getLogger(__name__)
_MAX_STORED_EVENTS = 80


class ResearchNotReadyError(ValueError):
    pass


def build_research_provider() -> ResearchProvider:
    """Return the configured provider; the current repository has no provider configured."""
    return UnconfiguredResearchProvider()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def research_session() -> Session:
    """Open an independent session for a request-scoped background task."""
    return Session(get_engine())


def research_state(investigation: Investigation) -> dict[str, object]:
    return {
        "investigation_id": investigation.id,
        "status": investigation.status,
        "progress": investigation.progress,
        "research_mode": investigation.research_mode,
        "research_progress": investigation.research_progress,
        "error_message": investigation.error_message,
    }


def start_research(db: Session, investigation_id: UUID) -> tuple[Investigation, ResearchProvider]:
    investigation = db.scalar(
        select(Investigation).where(Investigation.id == investigation_id)
        .with_for_update().execution_options(populate_existing=True)
    )
    if investigation is None:
        raise LookupError("Investigation not found")
    if investigation.status != "PLANNED":
        raise ResearchNotReadyError("Investigation is not ready for research.")
    if investigation.plan is None:
        raise ResearchNotReadyError("Investigation plan is missing.")

    plan = InvestigationPlan.model_validate(investigation.plan)
    queries = ResearchAgent().generate_queries(plan)
    if not queries:
        raise ResearchNotReadyError("Investigation plan contains no research steps.")

    provider = build_research_provider()
    now = utc_now()
    progress: dict[str, object] = {
        "mode": provider.mode,
        "current_step": None,
        "completed_steps": 0,
        "total_steps": len(queries),
        "current_query": None,
        "sources_found": 0,
        "evidence_found": 0,
        "entities_found": 0,
        "relationships_found": 0,
        "elapsed_seconds": 0,
        "started_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "finished_at": None,
        "message": "Research is starting.",
        "events": [],
    }
    _append_event(progress, "research_started", "Investigation research started.")
    investigation.status = "RESEARCHING"
    investigation.progress = 1
    investigation.research_mode = provider.mode
    investigation.research_progress = progress
    investigation.error_message = None
    db.commit()
    db.refresh(investigation)
    return investigation, provider


def run_research_background(investigation_id: UUID) -> None:
    """Execute research in a separate session after the HTTP response is sent."""
    try:
        with research_session() as db:
            execute_research(db, investigation_id, build_research_provider(), ResearchAgent())
    except Exception:
        # If PostgreSQL itself is unavailable, state cannot be advanced; keep diagnostics server-side.
        logger.exception("Unable to open a research session for investigation %s", investigation_id)


def execute_research(
    db: Session,
    investigation_id: UUID,
    provider: ResearchProvider,
    agent: ResearchAgent | None = None,
) -> Investigation:
    """Run the persisted plan step by step and commit source-backed discoveries."""
    research_agent = agent or ResearchAgent()
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise LookupError("Investigation not found")
    if investigation.status != "RESEARCHING" or investigation.plan is None:
        raise ResearchNotReadyError("Investigation is not ready for research.")

    plan = InvestigationPlan.model_validate(investigation.plan)
    queries = research_agent.generate_queries(plan)
    if not queries:
        raise ResearchNotReadyError("Investigation plan contains no research steps.")

    progress = dict(investigation.research_progress or {})
    started_at = _read_datetime(progress.get("started_at")) or utc_now()
    progress["mode"] = provider.mode
    progress["total_steps"] = len(queries)
    investigation.research_mode = provider.mode
    db.commit()

    try:
        existing_entities = {
            entity.name.casefold(): entity
            for entity in db.scalars(
                select(Entity).where(Entity.investigation_id == investigation_id)
            ).all()
        }
        existing_relationships = {
            (row.source_entity_id, row.target_entity_id, row.relationship_type.upper()): row
            for row in db.scalars(
                select(Relationship).where(Relationship.investigation_id == investigation_id)
            ).all()
        }
        for index, query in enumerate(queries):
            progress["current_step"] = query.step_id
            progress["current_query"] = query.query
            progress["updated_at"] = utc_now().isoformat()
            progress["message"] = f"Searching step {index + 1} of {len(queries)}."
            _append_event(
                progress,
                "research_step_started",
                f"Research step {index + 1} started.",
                step_id=query.step_id,
                query=query.query,
            )
            _append_event(progress, "query_started", "Plan-derived query started.", step_id=query.step_id, query=query.query)
            _save_progress(db, investigation, progress)

            batch = _search_with_timeout(provider, query)
            for received in batch.results:
                result = _normalize_result(received, query)
                evidence = _persist_evidence(db, investigation, result, provider.mode)
                progress["sources_found"] = int(progress.get("sources_found", 0)) + 1
                progress["evidence_found"] = int(progress.get("evidence_found", 0)) + 1
                _append_event(
                    progress,
                    "source_discovered",
                    f"Source discovered: {result.source_title}",
                    step_id=query.step_id,
                    query=query.query,
                )
                _append_event(
                    progress,
                    "evidence_created",
                    "Evidence provenance saved.",
                    step_id=query.step_id,
                    query=query.query,
                )

                extracted_entities = research_agent.extract_entities(result, plan, str(evidence.id))
                entity_rows: dict[str, Entity] = {}
                for candidate in extracted_entities:
                    entity, created = _upsert_entity(
                        db,
                        investigation,
                        candidate,
                        evidence,
                        provider.mode,
                        existing_entities,
                    )
                    entity_rows[candidate.name.casefold()] = entity
                    if created:
                        progress["entities_found"] = int(progress.get("entities_found", 0)) + 1
                        _append_event(
                            progress,
                            "entity_discovered",
                            f"Entity discovered: {entity.name}",
                            step_id=query.step_id,
                            query=query.query,
                        )

                extracted_relationships = research_agent.extract_relationships(result, plan)
                for candidate in extracted_relationships:
                    if not candidate.evidence_text.strip() or candidate.evidence_text.casefold() not in result.content.casefold():
                        continue
                    source_entity = entity_rows.get(candidate.source_entity.casefold())
                    target_entity = entity_rows.get(candidate.target_entity.casefold())
                    if source_entity is None:
                        source_entity, created = _upsert_entity(
                            db,
                            investigation,
                            _relationship_entity(candidate.source_entity, evidence.id, plan),
                            evidence,
                            provider.mode,
                            existing_entities,
                        )
                        if created:
                            progress["entities_found"] = int(progress.get("entities_found", 0)) + 1
                        entity_rows[candidate.source_entity.casefold()] = source_entity
                    if target_entity is None:
                        target_entity, created = _upsert_entity(
                            db,
                            investigation,
                            _relationship_entity(candidate.target_entity, evidence.id, plan),
                            evidence,
                            provider.mode,
                            existing_entities,
                        )
                        if created:
                            progress["entities_found"] = int(progress.get("entities_found", 0)) + 1
                        entity_rows[candidate.target_entity.casefold()] = target_entity

                    rel_key = (source_entity.id, target_entity.id, candidate.relationship_type.upper())
                    relationship = existing_relationships.get(rel_key)
                    if relationship is None:
                        relationship = Relationship(
                            source_entity_id=source_entity.id,
                            target_entity_id=target_entity.id,
                            investigation_id=investigation.id,
                            relationship_type=candidate.relationship_type.upper(),
                            confidence=candidate.confidence,
                            source=result.source_domain,
                            evidence_summary=candidate.evidence_text,
                            verification_status="needs_review",
                            confidence_score=candidate.confidence,
                            strength=candidate.confidence,
                            metadata_json={
                                "research_mode": provider.mode,
                                "demo_only": provider.mode == "local_demo",
                                "source_evidence_ids": [str(evidence.id)],
                            },
                        )
                        db.add(relationship)
                        db.flush()
                        existing_relationships[rel_key] = relationship
                        progress["relationships_found"] = int(progress.get("relationships_found", 0)) + 1
                        _append_event(
                            progress,
                            "relationship_discovered",
                            f"Evidence-backed relationship discovered: {candidate.relationship_type}",
                            step_id=query.step_id,
                            query=query.query,
                        )
                    else:
                        metadata = dict(relationship.metadata_json or {})
                        evidence_ids = list(metadata.get("source_evidence_ids", []))
                        if str(evidence.id) not in evidence_ids:
                            evidence_ids.append(str(evidence.id))
                        metadata["source_evidence_ids"] = evidence_ids
                        relationship.metadata_json = metadata
                    evidence.relationship_id = relationship.id

                db.flush()
                _save_progress(db, investigation, progress)

            progress["completed_steps"] = index + 1
            progress["current_step"] = query.step_id
            progress["updated_at"] = utc_now().isoformat()
            progress["elapsed_seconds"] = round((utc_now() - started_at).total_seconds(), 2)
            progress["message"] = f"Research step {index + 1} completed."
            _append_event(progress, "research_step_completed", f"Research step {index + 1} completed.", step_id=query.step_id, query=query.query)
            investigation.progress = round(5 + ((index + 1) / len(queries)) * 90, 2)
            _save_progress(db, investigation, progress)

        now = utc_now()
        progress["current_query"] = None
        progress["finished_at"] = now.isoformat()
        progress["updated_at"] = now.isoformat()
        progress["elapsed_seconds"] = round((now - started_at).total_seconds(), 2)
        if provider.mode == "local_demo":
            progress["message"] = (
                "Demo research mode — external source discovery is not configured. "
                "No source records or findings were generated."
            )
        else:
            progress["message"] = "Research completed. Discovered relationships are pending verification."
        _append_event(progress, "research_completed", str(progress["message"]))
        investigation.status = "COMPLETED"
        investigation.progress = 100
        investigation.error_message = None
        _save_progress(db, investigation, progress)
        return investigation
    except Exception as exc:
        logger.exception("Research failed for investigation %s", investigation_id)
        db.rollback()
        failed = db.get(Investigation, investigation_id)
        if failed is not None:
            progress = dict(failed.research_progress or progress)
            now = utc_now()
            progress["updated_at"] = now.isoformat()
            progress["finished_at"] = now.isoformat()
            progress["elapsed_seconds"] = round((now - started_at).total_seconds(), 2)
            progress["message"] = "Research could not be completed."
            _append_event(progress, "research_failed", "Research could not be completed.")
            failed.status = "FAILED"
            failed.error_message = "Research could not be completed."
            failed.research_progress = progress
            db.commit()
        raise ResearchExecutionError("Research could not be completed.") from exc


class ResearchExecutionError(RuntimeError):
    pass


def _search_with_timeout(provider: ResearchProvider, query: ResearchQuery) -> ResearchBatch:
    timeout = max(0.1, float(provider.timeout_seconds))
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="research-provider")
    future = executor.submit(provider.search, query)
    try:
        batch = future.result(timeout=timeout)
    except FutureTimeoutError as exc:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise TimeoutError("Research provider timed out") from exc
    except Exception:
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    executor.shutdown(wait=True)
    return batch


def _normalize_result(result: ResearchResult, query: ResearchQuery) -> ResearchResult:
    safe_url = validate_fetch_url(str(result.source_url))
    parsed = urlsplit(safe_url)
    return result.model_copy(
        update={
            "query": query.query,
            "source_url": safe_url,
            "source_domain": (parsed.hostname or result.source_domain).lower(),
            "research_step": query.purpose,
        }
    )


def _persist_evidence(
    db: Session,
    investigation: Investigation,
    result: ResearchResult,
    mode: str,
) -> Evidence:
    evidence = Evidence(
        investigation_id=investigation.id,
        relationship_id=None,
        source=result.source_domain,
        source_type=result.source_type,
        published_date=None,
        captured_at=result.retrieved_at,
        confidence=result.relevance,
        verification_status="needs_review",
        excerpt=result.content,
        source_url=str(result.source_url),
        title=result.source_title,
        content=result.content,
        evidence_type="research_source",
        confidence_score=result.relevance or 0,
        collected_at=result.retrieved_at,
        metadata_json={
            "provider_metadata": result.metadata,
            "research_mode": mode,
            "demo_only": mode == "local_demo",
            "provider": result.provider,
            "query": result.query,
            "research_step": result.research_step,
            "source_domain": result.source_domain,
            "relevance": result.relevance,
        },
    )
    db.add(evidence)
    db.flush()
    return evidence


def _upsert_entity(
    db: Session,
    investigation: Investigation,
    candidate: ExtractedEntity,
    evidence: Evidence,
    mode: str,
    existing: dict[str, Entity],
) -> tuple[Entity, bool]:
    key = candidate.name.casefold()
    entity = existing.get(key)
    if entity is None:
        entity = Entity(
            name=candidate.name,
            entity_type=candidate.entity_type.upper(),
            investigation_id=investigation.id,
            description=candidate.description,
            identifiers=candidate.aliases,
            metadata_json={
                "research_mode": mode,
                "demo_only": mode == "local_demo",
                "confidence": candidate.confidence,
                "source_evidence_ids": [str(evidence.id)],
            },
        )
        db.add(entity)
        db.flush()
        existing[key] = entity
        return entity, True

    metadata = dict(entity.metadata_json or {})
    evidence_ids = list(metadata.get("source_evidence_ids", []))
    if str(evidence.id) not in evidence_ids:
        evidence_ids.append(str(evidence.id))
    metadata["source_evidence_ids"] = evidence_ids
    metadata["confidence"] = max(float(metadata.get("confidence", 0)), candidate.confidence)
    entity.metadata_json = metadata
    aliases = list(entity.identifiers or [])
    entity.identifiers = list(dict.fromkeys([*aliases, *candidate.aliases]))
    return entity, False


def _relationship_entity(name: str, evidence_id: UUID, plan: InvestigationPlan) -> ExtractedEntity:
    is_target = bool(plan.target and name.casefold() == plan.target.casefold())
    return ExtractedEntity(
        name=name,
        entity_type="COMPANY" if is_target else "OTHER",
        source_evidence_ids=[str(evidence_id)],
        confidence=0.5,
    )


def _save_progress(db: Session, investigation: Investigation, progress: dict[str, object]) -> None:
    progress["updated_at"] = utc_now().isoformat()
    investigation.research_progress = dict(progress)
    db.commit()


def _append_event(
    progress: dict[str, object],
    event_type: str,
    message: str,
    *,
    step_id: str | None = None,
    query: str | None = None,
) -> None:
    events_value = progress.get("events", [])
    events = list(events_value) if isinstance(events_value, list) else []
    event: dict[str, object] = {"at": utc_now().isoformat(), "type": event_type, "message": message}
    if step_id is not None:
        event["step_id"] = step_id
    if query is not None:
        event["query"] = query
    events.append(event)
    progress["events"] = events[-_MAX_STORED_EVENTS:]


def _read_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None
