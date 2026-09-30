from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.relationship import Relationship
from graph.graph_builder import build_graph
from graph.graph_serializer import serialize_graph
from graph.graph_traversal import traverse
from graph.path_finder import shortest_path as find_shortest_path


def neighborhood(db: Session, entity_id: UUID, depth: int = 1) -> dict:
    relationships = list(db.scalars(select(Relationship)))
    graph = build_graph(relationships)
    reached = traverse(graph, str(entity_id), max_depth=depth, direction="both")
    depths = {node_id: hops for node_id, hops in reached}
    node_uuids = [UUID(node_id) for node_id in depths]
    entities = list(db.scalars(select(Entity).where(Entity.id.in_(node_uuids)))) if node_uuids else []
    edges = [edge for edge in graph.edges if edge.source in depths and edge.target in depths]
    selected_graph = build_graph([
        {"id": edge.id, "source": edge.source, "target": edge.target, "type": edge.relationship_type, "confidence": edge.confidence}
        for edge in edges
    ])
    node_metadata = {str(entity.id): {"name": entity.name, "type": entity.entity_type, "depth": depths[str(entity.id)]} for entity in entities}
    return serialize_graph(selected_graph, node_metadata)


def shortest_path(db: Session, source_id: UUID, target_id: UUID) -> list[str] | None:
    graph = build_graph(db.scalars(select(Relationship)))
    return find_shortest_path(graph, str(source_id), str(target_id), direction="both")
