"""Supplier-count concentration features without inferred market shares."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def structural_concentration(dependency_count: int) -> tuple[float | None, str]:
    if dependency_count <= 0:
        return None, "No verified dependency edges are available for concentration analysis."
    score = 100.0 / dependency_count
    return score, f"{dependency_count} distinct verified dependency edge(s) are recorded; this is a supplier-count proxy, not a spend-share estimate."


def measured_hhi(dependencies: list[Mapping[str, Any]]) -> float | None:
    """Return a 0–100 concentration score only when every share is source-backed."""
    shares: list[float] = []
    for dependency in dependencies:
        metadata = dependency.get("metadata") or {}
        share = metadata.get("volume_share", metadata.get("share"))
        provenance = (
            metadata.get("volume_share_source")
            or metadata.get("share_source")
            or metadata.get("volume_share_evidence_ids")
            or metadata.get("share_evidence_ids")
        )
        if not provenance:
            return None
        try:
            value = float(share)
        except (TypeError, ValueError):
            return None
        if value < 0:
            return None
        shares.append(value / 100.0 if value > 1.0 else value)
    total = sum(shares)
    if not shares or total <= 0:
        return None
    normalized = [share / total for share in shares]
    return round(sum(share * share for share in normalized) * 100.0, 2)
