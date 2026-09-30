import csv
import io
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.entity import Entity
from app.models.relationship import Relationship
from app.models.user import User

router = APIRouter(prefix="/exports", tags=["Exports"])


@router.get("/graph.json", summary="Export stored entities and relationships as graph JSON")
def export_graph(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    nodes = list(db.scalars(select(Entity).order_by(Entity.name)))
    edges = list(db.scalars(select(Relationship).order_by(Relationship.discovered_at)))
    return {"nodes": [{"id": str(n.id), "name": n.name, "type": n.entity_type} for n in nodes], "edges": [{"id": str(e.id), "source": str(e.source_entity_id), "target": str(e.target_entity_id), "type": e.relationship_type, "confidence": e.confidence_score, "verification_status": e.verification_status} for e in edges]}


@router.get("/relationships.csv", summary="Export recorded relationships as CSV")
def export_relationships(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["id", "source_entity_id", "target_entity_id", "relationship_type", "confidence", "verification_status"])
    for edge in db.scalars(select(Relationship).order_by(Relationship.discovered_at)):
        writer.writerow([edge.id, edge.source_entity_id, edge.target_entity_id, edge.relationship_type, edge.confidence_score, edge.verification_status])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=relationships.csv"})
