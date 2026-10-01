"""Find providers shared by multiple verified dependency paths."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any


def detect_common_dependencies(
    dependencies: list[Mapping[str, Any]],
    *,
    minimum_consumers: int = 2,
) -> list[dict[str, Any]]:
    """Report verified providers used by distinct consumers.

    `dependencies` must already contain only verified, non-demo edges in
    consumer-to-provider orientation. A shared provider is a graph pattern; it
    does not prove market share, exclusivity, or lack of substitutes.
    """
    by_provider: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for dependency in dependencies:
        by_provider[str(dependency["target_id"])].append(dependency)

    patterns: list[dict[str, Any]] = []
    for provider_id, rows in sorted(by_provider.items()):
        consumers = sorted({str(row["source_id"]) for row in rows})
        if len(consumers) < max(2, minimum_consumers):
            continue
        relationship_ids = sorted({str(row["relationship_id"]) for row in rows})
        count = len(consumers)
        patterns.append({
            "type": "COMMON_DEPENDENCY",
            "entity_id": provider_id,
            "related_entity_ids": consumers,
            "relationship_ids": relationship_ids,
            "explanation": (
                f"The verified graph links {count} distinct consumer entities to this provider. "
                "This shared dependency pattern does not establish spend share, exclusivity, or substitute availability."
            ),
            "severity": "HIGH" if count >= 5 else "MEDIUM",
        })
    return patterns
