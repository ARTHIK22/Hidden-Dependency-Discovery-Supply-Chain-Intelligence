from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.relationship import Relationship
from graph.graph_builder import build_graph
from risk_engine.risk_engine import analyze_risks


def analyze_supplier_risk(db: Session) -> list[dict]:
    """Return explainable graph-based signals; never label them external threats."""
    relationships = list(db.scalars(select(Relationship)))
    entities = {str(entity.id): entity for entity in db.scalars(select(Entity))}
    graph_result = analyze_risks(build_graph(relationships))
    risks = graph_result["risks"]
    for risk in risks:
        entity_id = risk.get("entity_id") or risk.get("supplier_id")
        if entity_id and entity_id in entities:
            risk["entity_name"] = entities[entity_id].name
    return risks
