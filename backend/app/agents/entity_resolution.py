"""Deterministic, evidence-aware entity matching without destructive merges."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Iterable


AUTO_MERGE_THRESHOLD = 0.95
_LEGAL_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited",
    "llc", "plc", "gmbh", "ag", "sa", "sarl", "pte", "pty", "bv", "nv", "lp", "llp",
}


def normalize_name(value: str) -> str:
    """Return a stable comparison key; the original display name is never modified."""
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(char for char in value if not unicodedata.combining(char))
    words = re.findall(r"[a-z0-9]+", value)
    while words and words[-1] in _LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words)


@dataclass(frozen=True)
class EntityResolutionResult:
    source_entity_id: str
    canonical_entity_id: str | None
    match_type: str
    confidence: float
    reasons: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    candidate_entity_id: str | None = None


def _aliases(entity: Any) -> set[str]:
    values: Iterable[Any] = entity.identifiers or []
    metadata = entity.metadata_json or {}
    values = [*values, *(metadata.get("aliases") or [])]
    normalized: set[str] = set()
    for value in values:
        if isinstance(value, str):
            key = normalize_name(value)
        elif isinstance(value, dict):
            key = normalize_name(str(value.get("value") or value.get("name") or ""))
        else:
            continue
        if key:
            normalized.add(key)
    return normalized


def _strong_identifiers(entity: Any) -> set[str]:
    metadata = entity.metadata_json or {}
    values = metadata.get("identifiers") or []
    found: set[str] = set()
    for item in values:
        if isinstance(item, dict):
            value = item.get("value")
        else:
            value = item
        if isinstance(value, str) and value.strip():
            found.add(value.strip().casefold())
    return found


def _evidence_ids(entity: Any) -> set[str]:
    return {str(value) for value in (entity.metadata_json or {}).get("source_evidence_ids", [])}


def _pair(left: Any, right: Any) -> tuple[str, float, tuple[str, ...]] | None:
    if str(left.entity_type).casefold() != str(right.entity_type).casefold():
        return None
    left_name = normalize_name(left.name)
    right_name = normalize_name(right.name)
    if not left_name or not right_name:
        return None
    left_aliases, right_aliases = _aliases(left), _aliases(right)
    shared_ids = _strong_identifiers(left) & _strong_identifiers(right)
    explicit_alias = left_name in right_aliases or right_name in left_aliases
    surface_equal = str(left.name).strip().casefold() == str(right.name).strip().casefold()
    same_evidence = bool(_evidence_ids(left) & _evidence_ids(right))
    description_left = normalize_name(getattr(left, "description", None) or "")
    description_right = normalize_name(getattr(right, "description", None) or "")
    description_similarity = SequenceMatcher(None, description_left, description_right).ratio() if description_left and description_right else 0.0
    same_jurisdiction = bool(left.jurisdiction and right.jurisdiction and left.jurisdiction.strip().casefold() == right.jurisdiction.strip().casefold())

    if shared_ids or explicit_alias:
        reasons = ("entity types match", "shared explicit alias or identifier")
        if same_evidence:
            reasons += ("both records cite at least one of the same evidence records",)
        return "ALIAS", 0.99, reasons
    if left_name == right_name:
        if same_jurisdiction and description_similarity >= 0.5:
            return "CONTEXTUAL", 0.96, ("normalized names match", "jurisdiction and descriptions provide matching context")
        reason = "display names match exactly" if surface_equal else "normalized names match after legal-suffix normalization"
        return "POSSIBLE_DUPLICATE", 0.88, (reason, "identity evidence and context are insufficient for automatic resolution")

    similarity = SequenceMatcher(None, left_name, right_name).ratio()
    if similarity >= 0.72:
        confidence = min(0.94, 0.60 + 0.22 * similarity + (0.08 if same_evidence else 0.0) + (0.06 if description_similarity >= 0.6 else 0.0))
        return "POSSIBLE_DUPLICATE", round(confidence, 4), ("entity types match", "names are similar but identity evidence is incomplete")
    return None


def resolve_entities(entities: list[Any], *, target_name: str | None = None, auto_merge_threshold: float = AUTO_MERGE_THRESHOLD) -> dict[str, EntityResolutionResult]:
    """Group only high-confidence matches; preserve every source entity row."""
    rows = sorted(entities, key=lambda row: str(row.id))
    parent = {str(row.id): str(row.id) for row in rows}
    candidates: dict[str, list[tuple[str, float, str, tuple[str, ...]]]] = {str(row.id): [] for row in rows}

    def root(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for index, left in enumerate(rows):
        for right in rows[index + 1:]:
            match = _pair(left, right)
            if match is None:
                continue
            kind, confidence, reasons = match
            left_id, right_id = str(left.id), str(right.id)
            candidates[left_id].append((right_id, confidence, kind, reasons))
            candidates[right_id].append((left_id, confidence, kind, reasons))
            if confidence >= auto_merge_threshold:
                parent[root(right_id)] = root(left_id)

    groups: dict[str, list[Any]] = {}
    for row in rows:
        groups.setdefault(root(str(row.id)), []).append(row)

    target_key = normalize_name(target_name or "")
    results: dict[str, EntityResolutionResult] = {}
    for group in groups.values():
        canonical = max(
            group,
            key=lambda row: (
                bool(target_key and normalize_name(row.name) == target_key),
                len(_evidence_ids(row)),
                bool(row.description),
                len(row.name),
                str(getattr(row, "created_at", "")),
                str(row.id),
            ),
        )
        canonical_id = str(canonical.id)
        for row in group:
            row_id = str(row.id)
            if len(group) > 1:
                group_matches = [entry for entry in candidates[row_id] if entry[0] in {str(item.id) for item in group}]
                confidence = max((entry[1] for entry in group_matches), default=1.0)
                kind = max(group_matches, key=lambda entry: entry[1])[2] if group_matches else "NORMALIZED"
                reasons = max(group_matches, key=lambda entry: entry[1])[3] if group_matches else ("resolved through a high-confidence entity group",)
                results[row_id] = EntityResolutionResult(row_id, canonical_id, kind, confidence, reasons, tuple(sorted(_evidence_ids(row))))
            else:
                possible = max(candidates[row_id], key=lambda entry: entry[1], default=None)
                if possible:
                    results[row_id] = EntityResolutionResult(row_id, None, "POSSIBLE_DUPLICATE", possible[1], possible[3], tuple(sorted(_evidence_ids(row))), possible[0])
                else:
                    results[row_id] = EntityResolutionResult(row_id, row_id, "UNRESOLVED", 0.0, ("no duplicate candidate was found; entity identity remains unconfirmed",), tuple(sorted(_evidence_ids(row))))
    return results
