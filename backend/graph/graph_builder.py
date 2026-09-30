from dataclasses import dataclass, field
from typing import Hashable, Iterable


@dataclass(frozen=True)
class GraphEdge:
    id: str
    source: str
    target: str
    relationship_type: str
    confidence: float = 0.0


@dataclass
class Graph:
    edges: list[GraphEdge] = field(default_factory=list)
    outgoing: dict[str, list[GraphEdge]] = field(default_factory=dict)
    incoming: dict[str, list[GraphEdge]] = field(default_factory=dict)


def build_graph(relationships: Iterable[object]) -> Graph:
    """Build a directed graph from relationship records or mapping objects."""
    graph = Graph()
    for relationship in relationships:
        def value(name: str, fallback: str | None = None):
            if isinstance(relationship, dict):
                return relationship.get(name, relationship.get(fallback) if fallback else None)
            return getattr(relationship, name, getattr(relationship, fallback, None) if fallback else None)

        source = value("source_entity_id", "source")
        target = value("target_entity_id", "target")
        if source is None or target is None:
            raise ValueError("Relationship requires source and target entity IDs")
        edge = GraphEdge(
            id=str(value("id") or f"{source}:{value('relationship_type')}:{target}"),
            source=str(source),
            target=str(target),
            relationship_type=str(value("relationship_type", "type") or "CONNECTED_TO").upper(),
            confidence=float(value("confidence_score", "confidence") or 0.0),
        )
        if not 0 <= edge.confidence <= 1:
            raise ValueError("Relationship confidence must be between 0 and 1")
        graph.edges.append(edge)
        graph.outgoing.setdefault(edge.source, []).append(edge)
        graph.incoming.setdefault(edge.target, []).append(edge)
    return graph
