"""Deterministic, explicitly fictional supply-chain data for local demos."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Entity, Evidence, Investigation, Relationship, Risk, WatchlistEntry


DEMO_INVESTIGATION_NAME = "DEMO — Illustrative electronics supply chain"
DEMO_NOTICE = (
    "DEMO ONLY: This fictional relationship is included to exercise the application. "
    "It is not a factual claim and has not been externally verified."
)


def populate_demo_investigation(db: Session, investigation: Investigation) -> None:
    """Populate one investigation once; all evidence is marked illustrative."""
    existing = db.scalar(
        select(Entity.id).where(Entity.investigation_id == investigation.id).limit(1)
    )
    if existing is not None:
        return

    definitions = (
        ("Acme Electronics", "company", "DEMO FIXTURE — illustrative electronics assembler.", "Region E", 58, "Medium"),
        ("Supplier B", "supplier", "DEMO FIXTURE — illustrative component supplier.", "Region E", 72, "High"),
        ("Manufacturer B", "manufacturer", "DEMO FIXTURE — illustrative contract manufacturer.", "Region E", 49, "Medium"),
        ("Lithium", "material", "DEMO FIXTURE — illustrative battery material.", "Region E", 64, "Medium"),
        ("Processing Facility D", "facility", "DEMO FIXTURE — illustrative processing facility.", "Region E", 61, "Medium"),
        ("Region E", "region", "DEMO FIXTURE — fictional region used for the UI scenario.", "Region E", 43, "Low"),
    )
    entities = {
        name: Entity(
            name=name,
            entity_type=entity_type,
            investigation_id=investigation.id,
            description=description,
            jurisdiction=jurisdiction,
            risk_score=score,
            risk_level=level,
            identifiers=[],
        )
        for name, entity_type, description, jurisdiction, score, level in definitions
    }
    db.add_all(entities.values())
    db.flush()

    relationship_definitions = (
        ("Supplier B", "Acme Electronics", "SUPPLIES"),
        ("Acme Electronics", "Supplier B", "DEPENDS_ON"),
        ("Acme Electronics", "Lithium", "USES_MATERIAL"),
        ("Manufacturer B", "Acme Electronics", "MANUFACTURES"),
        ("Processing Facility D", "Lithium", "PROCESSES"),
        ("Processing Facility D", "Region E", "LOCATED_IN"),
    )
    relationships: list[Relationship] = []
    for source_name, target_name, relationship_type in relationship_definitions:
        relationship = Relationship(
            source_entity_id=entities[source_name].id,
            target_entity_id=entities[target_name].id,
            investigation_id=investigation.id,
            relationship_type=relationship_type,
            confidence=0.35,
            source="DEMO fixture — no external source verified",
            evidence_summary=DEMO_NOTICE,
            verification_status="demo_unverified",
            confidence_score=0.35,
            strength=0.35,
        )
        relationships.append(relationship)
    db.add_all(relationships)
    db.flush()

    db.add_all(
        Evidence(
            relationship_id=relationship.id,
            source="DEMO fixture — no external source verified",
            source_type="development_fixture",
            published_date=None,
            confidence=0.35,
            verification_status="demo_unverified",
            excerpt=DEMO_NOTICE,
            source_url=None,
                title="DEMO illustrative relationship evidence",
                content=DEMO_NOTICE,
                evidence_type="demo_fixture",
                confidence_score=0.35,
                metadata_json={"demo_only": True},
        )
        for relationship in relationships
    )

    risk_definitions = (
        ("Supplier B", 0.72, "High", "DEMO ONLY: illustrative concentration exposure; no real supplier data was analyzed."),
        ("Lithium", 0.64, "Medium", "DEMO ONLY: illustrative material dependency; no external market data was analyzed."),
        ("Processing Facility D", 0.51, "Medium", "DEMO ONLY: illustrative facility exposure; no facility records were verified."),
    )
    db.add_all(
        Risk(
            entity_id=entities[name].id,
            investigation_id=investigation.id,
            score=score,
            score_scale="fraction",
            level=level,
            reason=reason,
            risk_type="dependency_exposure",
            severity=level.lower(),
            title=reason[:240],
        )
        for name, score, level, reason in risk_definitions
    )

    db.add_all(
        (
            Alert(
                investigation_id=investigation.id,
                entity_id=entities["Supplier B"].id,
                title="DEMO: Illustrative supplier concentration",
                message="This fictional alert demonstrates the notification workflow. It is not a verified finding.",
                severity="high",
                alert_type="DEMO_FIXTURE",
            ),
            Alert(
                investigation_id=investigation.id,
                entity_id=entities["Lithium"].id,
                title="DEMO: Illustrative material dependency",
                message="This fictional alert is sample interface data, not a real-world risk notification.",
                severity="medium",
                alert_type="DEMO_FIXTURE",
            ),
        )
    )

    for name in ("Supplier B", "Lithium"):
        present = db.scalar(
            select(WatchlistEntry.id).where(WatchlistEntry.entity_id == entities[name].id)
        )
        if present is None:
            db.add(WatchlistEntry(
                entity_id=entities[name].id,
                target_type="entity",
                target_id=entities[name].id,
                target_key=f"entity:{entities[name].id}",
                status="watching",
            ))


def seed_demo_data(db: Session) -> Investigation:
    """Create or reuse the stable workspace demo investigation and records."""
    investigation = db.scalar(
        select(Investigation).where(Investigation.name == DEMO_INVESTIGATION_NAME)
    )
    if investigation is None:
        investigation = Investigation(
            name=DEMO_INVESTIGATION_NAME,
            goal="DEMO ONLY: Explore a fictional electronics supply chain and inspect illustrative dependency records.",
            status="completed",
            progress=100,
            scope={"geography": True, "materials": True, "manufacturers": True, "verification": True},
            depth="standard",
            demo_mode=True,
        )
        db.add(investigation)
        db.flush()
    populate_demo_investigation(db, investigation)
    db.commit()
    db.refresh(investigation)
    return investigation
