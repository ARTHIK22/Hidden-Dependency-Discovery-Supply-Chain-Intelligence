from collections import deque

from graph.graph_builder import Graph


def propagate_risk(graph: Graph, source_scores: dict[str, float], decay: float = 0.8, max_depth: int = 5) -> dict[str, dict]:
    if not 0 <= decay <= 1:
        raise ValueError("decay must be between 0 and 1")
    propagated: dict[str, dict] = {}
    for source, score in source_scores.items():
        if not 0 <= score <= 1:
            raise ValueError("source risk scores must be between 0 and 1")
        visited = {str(source)}
        queue = deque([(str(source), float(score), 0)])
        while queue:
            node, current_score, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in graph.outgoing.get(node, []):
                target = edge.target
                candidate = current_score * decay * edge.confidence
                if target not in visited and candidate > 0:
                    visited.add(target)
                    prior = propagated.get(target, {}).get("score", 0.0)
                    if candidate > prior:
                        propagated[target] = {"score": round(candidate, 4), "severity": "high" if candidate >= 0.7 else "medium" if candidate >= 0.4 else "low", "source_entity_id": str(source), "hops": depth + 1}
                    queue.append((target, candidate, depth + 1))
    return propagated
