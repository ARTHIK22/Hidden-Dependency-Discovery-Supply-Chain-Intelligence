"""Bounded downstream-to-upstream risk propagation over verified dependencies."""

from __future__ import annotations

from collections.abc import Iterable


def propagate_risk(
    local_scores: dict[str, float | None],
    edges: Iterable[tuple[str, str, float | None]],
    *,
    max_depth: int = 6,
    decay: float = 0.72,
) -> dict[str, float | None]:
    """Propagate provider risk toward dependents using prior-hop values only.

    Edges are consumer -> provider. Unknown confidence prevents propagation over
    that edge. Each iteration represents one graph hop, so cycles are bounded.
    """
    current = {node: score for node, score in local_scores.items()}
    ordered_edges = sorted(edges, key=lambda edge: (edge[0], edge[1]))
    for _ in range(max_depth):
        next_scores = dict(current)
        for consumer, provider, confidence in ordered_edges:
            provider_score = current.get(provider)
            if provider_score is None or confidence is None:
                continue
            candidate = round(provider_score * max(0.0, min(1.0, confidence)) * decay, 2)
            existing = next_scores.get(consumer)
            if existing is None or candidate > existing:
                next_scores[consumer] = candidate
        current = next_scores
    return current
