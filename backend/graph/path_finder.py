from collections import deque

from graph.graph_builder import Graph
from graph.graph_traversal import adjacent_edges


def shortest_path(graph: Graph, source: str, target: str, direction: str = "both", max_depth: int | None = None) -> list[str] | None:
    source, target = str(source), str(target)
    if max_depth is not None and max_depth < 0:
        raise ValueError("max_depth cannot be negative")
    parents: dict[str, str | None] = {source: None}
    queue = deque([(source, 0)])
    while queue:
        node, depth = queue.popleft()
        if node == target:
            path = []
            while node is not None:
                path.append(node)
                node = parents[node]
            return list(reversed(path))
        if max_depth is not None and depth >= max_depth:
            continue
        for edge in adjacent_edges(graph, node, direction):
            neighbor = edge.source if direction == "incoming" else edge.target if direction == "outgoing" else edge.target if edge.source == node else edge.source
            if neighbor not in parents:
                parents[neighbor] = node
                queue.append((neighbor, depth + 1))
    return None
