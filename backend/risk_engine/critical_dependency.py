from graph.graph_builder import Graph
from graph.graph_traversal import traverse


def identify_critical_nodes(graph: Graph, max_depth: int = 5) -> list[dict]:
    """Rank nodes by reachable downstream count, a transparent structural proxy."""
    nodes = {node for edge in graph.edges for node in (edge.source, edge.target)}
    ranked = []
    for node in nodes:
        reached = traverse(graph, node, max_depth=max_depth, direction="outgoing")
        downstream = [entity_id for entity_id, hops in reached if hops]
        if downstream:
            ranked.append({"entity_id": node, "downstream_count": len(downstream), "score": min(1.0, len(downstream) / max(1, len(nodes) - 1)), "explanation": "Ranked by the count of reachable downstream entities in recorded directed relationships."})
    return sorted(ranked, key=lambda item: (-item["downstream_count"], item["entity_id"]))
