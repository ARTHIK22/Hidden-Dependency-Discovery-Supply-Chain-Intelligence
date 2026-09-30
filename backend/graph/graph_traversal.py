from collections import deque

from graph.graph_builder import Graph


def adjacent_edges(graph: Graph, entity_id: str, direction: str = "both"):
    if direction == "outgoing":
        return graph.outgoing.get(str(entity_id), [])
    if direction == "incoming":
        return graph.incoming.get(str(entity_id), [])
    if direction != "both":
        raise ValueError("direction must be outgoing, incoming, or both")
    return [*graph.outgoing.get(str(entity_id), []), *graph.incoming.get(str(entity_id), [])]


def traverse(graph: Graph, start: str, max_depth: int = 1, direction: str = "both") -> list[tuple[str, int]]:
    if max_depth < 0:
        raise ValueError("max_depth cannot be negative")
    start = str(start)
    seen = {start}
    result = [(start, 0)]
    queue = deque([(start, 0)])
    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for edge in adjacent_edges(graph, node, direction):
            if direction == "incoming":
                neighbor = edge.source
            elif direction == "outgoing":
                neighbor = edge.target
            else:
                neighbor = edge.target if edge.source == node else edge.source
            if neighbor not in seen:
                seen.add(neighbor)
                result.append((neighbor, depth + 1))
                queue.append((neighbor, depth + 1))
    return result
