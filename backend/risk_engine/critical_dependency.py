"""Explainable dependency patterns detected from the verified graph."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping
import heapq
from typing import Any

from .concentration import measured_hhi
from .common_dependency import detect_common_dependencies


def detect_critical_dependencies(
    entities: Mapping[str, Mapping[str, Any]],
    dependencies: list[Mapping[str, Any]],
    *,
    minimum_deep_edges: int = 4,
    geographic_share_threshold: float = 0.67,
    maximum_depth: int = 6,
) -> list[dict[str, Any]]:
    outgoing: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in dependencies:
        source = str(edge["source_id"])
        target = str(edge["target_id"])
        outgoing[source].append(edge)
        adjacency[source].append(target)

    detected: list[dict[str, Any]] = []
    for source_id in sorted(outgoing):
        rows = outgoing[source_id]
        if len(rows) == 1:
            edge = rows[0]
            detected.append(_pattern(
                "SINGLE_SOURCE", source_id, [str(edge["target_id"])], [str(edge["relationship_id"])],
                "The verified graph records exactly one direct dependency; alternatives are not represented by the available evidence.",
                "HIGH",
            ))

        shares = [
            {"metadata": edge.get("metadata") or {}}
            for edge in rows
        ]
        hhi = measured_hhi(shares)
        if hhi is not None and hhi >= 25.0 and len(rows) > 1:
            detected.append(_pattern(
                "HIGH_CONCENTRATION", source_id,
                [str(edge["target_id"]) for edge in rows],
                [str(edge["relationship_id"]) for edge in rows],
                f"Source-backed dependency shares produce a concentration index of {hhi:g}/100.",
                "HIGH" if hhi >= 50 else "MEDIUM",
            ))

        jurisdictions: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for edge in rows:
            target = entities.get(str(edge["target_id"]), {})
            jurisdiction = target.get("jurisdiction")
            if isinstance(jurisdiction, str) and jurisdiction.strip():
                jurisdictions[jurisdiction.strip().casefold()].append(edge)
        known_count = sum(len(value) for value in jurisdictions.values())
        if known_count >= 2:
            region, region_edges = sorted(jurisdictions.items(), key=lambda item: (-len(item[1]), item[0]))[0]
            share = len(region_edges) / known_count
            if share >= geographic_share_threshold:
                detected.append(_pattern(
                    "GEOGRAPHIC_CONCENTRATION", source_id,
                    [str(edge["target_id"]) for edge in region_edges],
                    [str(edge["relationship_id"]) for edge in region_edges],
                    f"{len(region_edges)} of {known_count} jurisdiction-tagged direct dependencies share recorded jurisdiction '{region}'.",
                    "MEDIUM",
                ))

    deep_path = _deepest_path(adjacency, maximum_depth)
    if len(deep_path) - 1 >= minimum_deep_edges:
        detected.append(_pattern(
            "DEEP_DEPENDENCY", deep_path[0], deep_path[1:], [],
            f"A verified dependency chain contains {len(deep_path) - 1} edges, meeting the configured depth threshold of {minimum_deep_edges}.",
            "MEDIUM",
        ))

    for edge in dependencies:
        target_id = str(edge["target_id"])
        target = entities.get(target_id, {})
        entity_type = str(target.get("entity_type", "")).casefold()
        if "material" in entity_type or entity_type in {"mineral", "raw_material"}:
            detected.append(_pattern(
                "MATERIAL_DEPENDENCY", str(edge["source_id"]), [target_id],
                [str(edge["relationship_id"])],
                f"The verified relationship points to an entity typed '{target.get('entity_type')}'. Material criticality is scored only when source metadata records it.",
                "INFO",
            ))

    detected.extend(detect_common_dependencies(dependencies))

    return sorted(detected, key=lambda item: (item["type"], item["entity_id"], tuple(item["related_entity_ids"])))


def _deepest_path(adjacency: Mapping[str, list[str]], maximum_depth: int) -> list[str]:
    nodes = set(adjacency)
    indegree: dict[str, int] = {node: 0 for node in nodes}
    for neighbors in adjacency.values():
        for neighbor in neighbors:
            nodes.add(neighbor)
            indegree.setdefault(neighbor, 0)
            indegree[neighbor] += 1
    ready = [node for node, count in indegree.items() if count == 0]
    heapq.heapify(ready)
    topological: list[str] = []
    while ready:
        node = heapq.heappop(ready)
        topological.append(node)
        for neighbor in sorted(adjacency.get(node, [])):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                heapq.heappush(ready, neighbor)

    if len(topological) == len(nodes):
        depth = {node: 1 for node in nodes}
        parent: dict[str, str | None] = {node: None for node in nodes}
        for node in topological:
            if depth[node] >= maximum_depth + 1:
                continue
            for neighbor in sorted(adjacency.get(node, [])):
                candidate = depth[node] + 1
                if candidate > depth[neighbor] or (
                    candidate == depth[neighbor]
                    and (parent[neighbor] is None or node < parent[neighbor])
                ):
                    depth[neighbor] = candidate
                    parent[neighbor] = node
        endpoint = max(sorted(nodes), key=lambda node: depth[node], default=None)
        if endpoint is None:
            return []
        path: list[str] = []
        cursor: str | None = endpoint
        while cursor is not None:
            path.append(cursor)
            cursor = parent[cursor]
        return list(reversed(path))

    # A cycle has no topological longest path. Search simple paths with a hard
    # depth cap so cycles cannot create artificial infinite dependency chains.
    best: list[str] = []
    for start in sorted(adjacency):
        queue = deque([(start, [start])])
        visited = {start}
        while queue:
            node, path = queue.popleft()
            if (len(path), tuple(path)) > (len(best), tuple(best)):
                best = path
            if len(path) - 1 >= maximum_depth:
                continue
            for neighbor in sorted(adjacency.get(node, [])):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, [*path, neighbor]))
    return best


def _pattern(
    pattern_type: str,
    entity_id: str,
    related_entity_ids: list[str],
    relationship_ids: list[str],
    explanation: str,
    severity: str,
) -> dict[str, Any]:
    return {
        "type": pattern_type,
        "entity_id": entity_id,
        "related_entity_ids": sorted(set(related_entity_ids)),
        "relationship_ids": sorted(set(relationship_ids)),
        "explanation": explanation,
        "severity": severity,
    }
