from graph.graph_builder import Graph


def serialize_graph(graph: Graph, node_metadata: dict[str, dict] | None = None) -> dict:
    metadata = node_metadata or {}
    node_ids = {edge.source for edge in graph.edges} | {edge.target for edge in graph.edges} | set(metadata)
    return {
        "nodes": [{"id": node_id, **metadata.get(node_id, {})} for node_id in sorted(node_ids)],
        "edges": [{"id": edge.id, "source": edge.source, "target": edge.target, "type": edge.relationship_type, "confidence": edge.confidence} for edge in graph.edges],
    }
