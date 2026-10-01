"""Run an isolated seeded SQLite backend for browser tests."""

import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session


descriptor, database_path = tempfile.mkstemp(prefix="hdi-e2e-", suffix=".sqlite3")
os.close(descriptor)
os.environ["DATABASE_URL"] = f"sqlite:///{Path(database_path).as_posix()}"
os.environ["JWT_SECRET_KEY"] = "isolated-playwright-test-secret-32-bytes-minimum"
os.environ["APP_ENV"] = "development"
os.environ["DEMO_MODE"] = "true"

from sqlalchemy.orm import Session  # noqa: E402

from app.core.database import get_engine  # noqa: E402
from app.api.access import get_accessible_investigation  # noqa: E402
from app.api.dependencies import get_current_user  # noqa: E402
from app.demo_data import seed_demo_data  # noqa: E402
from app.main import app  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.models import Base, Entity, Evidence, Relationship  # noqa: E402


fixture_router = APIRouter(prefix="/api/e2e/monitoring", include_in_schema=False)


def _require_fixture_mode() -> None:
    if os.environ.get("HDI_E2E_FIXTURES") != "true":
        raise HTTPException(status_code=404, detail="Not found")


@fixture_router.post("/{investigation_id}/seed-anchor")
def seed_monitoring_anchor(
    investigation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict[str, str]:
    _require_fixture_mode()
    investigation = get_accessible_investigation(db, investigation_id, current_user)
    entity = db.scalar(select(Entity).where(
        Entity.investigation_id == investigation.id,
        Entity.name == "Acme Electronics",
    ))
    if entity is None:
        entity = Entity(
            name="Acme Electronics", entity_type="COMPANY", investigation_id=investigation.id,
            description="Synthetic E2E fixture anchor.", metadata_json={"test_fixture": True}, identifiers=[],
        )
        db.add(entity)
        db.commit()
        db.refresh(entity)
    return {"entity_id": str(entity.id)}


@fixture_router.post("/{investigation_id}/seed-change")
def seed_monitoring_change(
    investigation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict[str, str]:
    _require_fixture_mode()
    investigation = get_accessible_investigation(db, investigation_id, current_user)
    consumer = db.scalar(select(Entity).where(
        Entity.investigation_id == investigation.id,
        Entity.name == "Acme Electronics",
    ))
    if consumer is None:
        raise HTTPException(status_code=409, detail="Seed the monitoring anchor before the change.")
    suffix = uuid4().hex[:8]
    supplier = Entity(
        name=f"Lithium Processor {suffix}", entity_type="COMPANY", investigation_id=investigation.id,
        description="Synthetic E2E fixture supplier.", metadata_json={"test_fixture": True}, identifiers=[],
    )
    db.add(supplier)
    db.flush()
    relationship = Relationship(
        source_entity_id=supplier.id, target_entity_id=consumer.id, investigation_id=investigation.id,
        relationship_type="SUPPLIES", confidence=0.9, confidence_score=0.9, strength=0.9,
        verification_status="needs_review", evidence_summary="Deterministic E2E source statements.",
        metadata_json={"research_mode": "external", "test_fixture": True},
    )
    db.add(relationship)
    db.flush()
    evidence_ids = []
    for index, domain in enumerate(("registry.fixture.test", "disclosure.fixture.test")):
        statement = f"{supplier.name} supplies Acme Electronics."
        evidence = Evidence(
            investigation_id=investigation.id, relationship_id=relationship.id,
            source=domain, source_type="test_fixture", source_url=f"https://{domain}/supply/{suffix}/{index}",
            published_date=date.today(), captured_at=datetime.now(timezone.utc), confidence=0.9,
            verification_status="needs_review", excerpt=statement, title="Synthetic E2E source statement",
            content=statement, evidence_type="source_statement", confidence_score=0.9,
            metadata_json={"relevance": 0.95, "source_domain": domain, "research_mode": "external", "test_fixture": True},
        )
        db.add(evidence)
        db.flush()
        evidence_ids.append(str(evidence.id))
    relationship.metadata_json = {
        **(relationship.metadata_json or {}),
        "source_evidence_ids": evidence_ids,
    }
    db.commit()
    return {"entity_id": str(supplier.id), "relationship_id": str(relationship.id)}


app.include_router(fixture_router)


def main() -> None:
    engine = get_engine()
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            seed_demo_data(db)

        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")
    finally:
        engine.dispose()
        Path(database_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
