"""Deterministic evidence aggregation and relationship verification heuristics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from app.agents.entity_resolution import normalize_name


VERIFIED_THRESHOLD = 0.78
RELATION_TERMS: dict[str, tuple[str, ...]] = {
    "SUPPLIES": ("supply", "supplies", "supplied", "supplying", "supplier to", "supplier for"),
    "SUPPLIER_OF": ("supply", "supplies", "supplied", "supplier to", "supplier for"),
    "SUPPLIER": ("supply", "supplies", "supplied", "supplier to", "supplier for"),
    "MANUFACTURES": ("manufacture", "manufactures", "manufactured", "manufacturer", "produces"),
    "PRODUCES": ("produce", "produces", "produced", "manufactures"),
    "OWNS": ("owns", "owned by", "ownership"),
    "OWNED_BY": ("owned by", "owns", "acquired"),
    "SUBSIDIARY_OF": ("subsidiary of", "owned by", "acquired"),
    "LOCATED_IN": ("located in", "based in", "operates in", "facility in"),
    "PARTNER_OF": ("partner of", "partners with", "partnership with"),
    "DISTRIBUTES": ("distributes", "distributed", "distribution agreement"),
}
_NEGATION = re.compile(r"\b(no longer|ceased|stopped|discontinued|terminated|does not|do not|did not|never|not currently|ended its|ended the)\b", re.I)


@dataclass(frozen=True)
class VerificationResult:
    relationship_id: str
    status: str
    confidence: float
    evidence_ids: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    conflicting_evidence: tuple[str, ...]
    explanation: str
    verified_at: datetime | None
    details: dict[str, Any]


def _source_domain(evidence: Any) -> str | None:
    metadata = evidence.metadata_json or {}
    raw = evidence.source_url
    if raw:
        host = (urlsplit(raw).hostname or "").casefold().removeprefix("www.")
        if host:
            return host
    value = metadata.get("source_domain")
    if isinstance(value, str) and value.strip():
        return value.strip().casefold().removeprefix("www.")
    return None


def _endpoint_variants(entity: Any) -> set[str]:
    metadata = entity.metadata_json or {}
    names = [entity.name, *(metadata.get("aliases") or [])]
    for item in entity.identifiers or []:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict) and isinstance(item.get("value") or item.get("name"), str):
            names.append(item.get("value") or item.get("name"))
    return {normalize_name(name) for name in names if isinstance(name, str) and normalize_name(name)}


def _contains_endpoint(text: str, entity: Any) -> bool:
    normalized = f" {normalize_name(text)} "
    return any(f" {variant} " in normalized for variant in _endpoint_variants(entity))


def _terms_for(relationship_type: str) -> tuple[str, ...]:
    kind = relationship_type.strip().upper().replace("-", "_").replace(" ", "_")
    if kind in RELATION_TERMS:
        return RELATION_TERMS[kind]
    words = [part.replace("_", " ").casefold() for part in kind.split("_") if len(part) > 2]
    return tuple(words)


def _has_relation_term(text: str, relationship_type: str) -> bool:
    folded = " ".join(normalize_name(text).split())
    return any(" ".join(normalize_name(term).split()) in folded for term in _terms_for(relationship_type))


def _classify(evidence: Any, relation: Any, source: Any, target: Any) -> tuple[str, float, dict[str, Any]]:
    metadata = evidence.metadata_json or {}
    excerpt = " ".join(filter(None, [evidence.title, evidence.excerpt, evidence.content]))
    demo = bool(metadata.get("demo_only")) or "DEMO" in excerpt.upper()
    clauses = [part for part in re.split(r"[!?;\n]+|(?<=\.)\s+(?=[A-Z0-9])", excerpt) if part.strip()]
    direct_clauses = [
        clause for clause in clauses
        if _contains_endpoint(clause, source) and _contains_endpoint(clause, target)
        and _has_relation_term(clause, relation.relationship_type)
    ]
    positive_statement = any(not _NEGATION.search(clause) for clause in direct_clauses)
    negative_statement = any(bool(_NEGATION.search(clause)) for clause in direct_clauses)
    classification = "mixed" if positive_statement and negative_statement else "conflicting" if negative_statement else "supporting" if positive_statement else "unrelated"
    label = "unrelated" if demo else classification
    directness = 1.0 if label in {"supporting", "conflicting", "mixed"} else 0.0

    relevance = metadata.get("relevance")
    if not isinstance(relevance, (int, float)):
        relevance = evidence.confidence
    relevance_known = isinstance(relevance, (int, float))
    relevance_score = min(1.0, max(0.0, float(relevance))) if relevance_known else 0.5
    availability = 1.0 if evidence.source_url else 0.0
    published = evidence.published_date
    if isinstance(published, str):
        try:
            published = date.fromisoformat(published)
        except ValueError:
            published = None
    if isinstance(published, date):
        age_days = max(0, (datetime.now(timezone.utc).date() - published).days)
        recency = max(0.0, min(1.0, 1.0 - age_days / (3650.0)))
        recency_known = True
    else:
        recency, recency_known = 0.5, False
    authority = metadata.get("authority_score")
    authority_known = isinstance(authority, (int, float))
    authority_score = min(1.0, max(0.0, float(authority))) if authority_known else 0.5
    strength = 0.40 * relevance_score + 0.35 * directness + 0.10 * availability + 0.10 * recency + 0.05 * authority_score
    return label, strength, {
        "evidence_id": str(evidence.id), "classification": label,
        "score": round(strength, 4), "relevance": relevance_score,
        "relevance_known": relevance_known, "directness": directness,
        "source_available": bool(evidence.source_url), "recency": round(recency, 4),
        "recency_known": recency_known, "authority": authority_score,
        "authority_known": authority_known, "source_domain": _source_domain(evidence),
    }


def verify_relationship(relationship: Any, source_entity: Any, target_entity: Any, evidence_rows: list[Any], *, evaluated_at: datetime | None = None) -> VerificationResult:
    evaluated_at = evaluated_at or datetime.now(timezone.utc)
    detail_rows = [_classify(row, relationship, source_entity, target_entity) for row in evidence_rows]
    supporting = [row for row, item in zip(evidence_rows, detail_rows) if item[0] in {"supporting", "mixed"}]
    conflicting = [row for row, item in zip(evidence_rows, detail_rows) if item[0] in {"conflicting", "mixed"}]
    supporting_domains = {item[2]["source_domain"] for item in detail_rows if item[0] in {"supporting", "mixed"} and item[2]["source_domain"]}
    independent_sources = len(supporting_domains)
    relevant = len({str(row.id) for row in [*supporting, *conflicting]})
    conflict_ratio = len(conflicting) / relevant if relevant else 0.0
    extraction = getattr(relationship, "confidence", None)
    if not isinstance(extraction, (int, float)):
        extraction = getattr(relationship, "confidence_score", None)
    extraction_known = isinstance(extraction, (int, float))
    extraction_score = min(1.0, max(0.0, float(extraction))) if extraction_known else 0.5
    best_strength = max((item[1] for item in detail_rows if item[0] in {"supporting", "mixed"}), default=0.0)
    corroboration = min(1.0, max(0, independent_sources - 1) / 2.0)
    consistency = 0.5 if supporting and conflicting else 1.0 if supporting else 0.0 if conflicting else 0.5
    confidence = min(1.0, max(0.0, 0.55 * best_strength + 0.20 * corroboration + 0.15 * extraction_score + 0.10 * consistency - 0.35 * conflict_ratio))
    if not supporting and not conflicting:
        confidence = 0.0

    if supporting and conflicting:
        status = "CONFLICTED"
        explanation = "Available evidence includes both supporting and contradictory statements; both have been preserved."
    elif conflicting:
        status = "REJECTED"
        explanation = "Available evidence contradicts this relationship; it remains in the graph with its source evidence."
    elif not supporting:
        status = "INSUFFICIENT_EVIDENCE"
        explanation = "No direct, non-demo evidence was found that mentions both entities and this relationship."
    elif independent_sources >= 2 and confidence >= VERIFIED_THRESHOLD:
        status = "VERIFIED"
        explanation = "Verified from available evidence across independent source domains; this is an evidence assessment, not a claim of absolute truth."
    else:
        status = "SUPPORTED"
        explanation = "Available evidence supports this relationship, but it does not meet the multi-source verification threshold."

    verified_at = evaluated_at if status == "VERIFIED" else None
    details = {
        "formula": "clamp(0.55*best_evidence_strength + 0.20*corroboration + 0.15*extraction_confidence + 0.10*consistency - 0.35*conflict_ratio, 0, 1)",
        "evidence_strength_formula": "0.40*relevance + 0.35*directness + 0.10*source_availability + 0.10*recency + 0.05*authority",
        "evidence_scores": [item[2] for item in detail_rows],
        "independent_source_domains": sorted(supporting_domains),
        "independent_source_count": independent_sources,
        "corroboration": round(corroboration, 4), "extraction_confidence": extraction_score,
        "extraction_confidence_known": extraction_known, "consistency": consistency,
        "conflict_ratio": round(conflict_ratio, 4), "verified_threshold": VERIFIED_THRESHOLD,
        "evaluated_at": evaluated_at.isoformat(),
        "source_dates": sorted({row.published_date.isoformat() for row in evidence_rows if getattr(row, "published_date", None)}),
        "first_seen": (min((row.captured_at for row in evidence_rows if getattr(row, "captured_at", None)), default=None).isoformat()
                       if any(getattr(row, "captured_at", None) for row in evidence_rows) else None),
        "last_seen": (max((row.captured_at for row in evidence_rows if getattr(row, "captured_at", None)), default=None).isoformat()
                      if any(getattr(row, "captured_at", None) for row in evidence_rows) else None),
    }
    return VerificationResult(
        str(relationship.id), status, round(confidence, 4), tuple(str(row.id) for row in evidence_rows),
        tuple(str(row.id) for row in supporting), tuple(str(row.id) for row in conflicting),
        explanation, verified_at, details,
    )
