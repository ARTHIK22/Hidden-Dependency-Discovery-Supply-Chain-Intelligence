from datetime import datetime, timezone


def calculate_confidence(*, source_reliabilities: list[float], evidence_confidences: list[float], contradiction_count: int = 0, freshness_days: int = 0) -> dict:
    if any(not 0 <= score <= 1 for score in [*source_reliabilities, *evidence_confidences]):
        raise ValueError("Confidence inputs must be between 0 and 1")
    if contradiction_count < 0 or freshness_days < 0:
        raise ValueError("Contradiction and freshness values cannot be negative")
    source = sum(source_reliabilities) / len(source_reliabilities) if source_reliabilities else 0.0
    evidence = sum(evidence_confidences) / len(evidence_confidences) if evidence_confidences else 0.0
    support = min(1.0, len(set(range(len(source_reliabilities)))) / 2) if source_reliabilities else 0.0
    freshness = max(0.0, 1.0 - freshness_days / 730)
    raw = 0.35 * source + 0.35 * evidence + 0.15 * support + 0.10 * freshness + 0.05
    score = round(max(0.0, raw - min(0.5, contradiction_count * 0.25)), 4)
    level = "high" if score >= 0.8 else "moderate" if score >= 0.55 else "low"
    factors = [f"mean source reliability {source:.2f}", f"mean evidence confidence {evidence:.2f}", f"{len(source_reliabilities)} supporting source(s)", f"freshness factor {freshness:.2f}"]
    if contradiction_count:
        factors.append(f"{contradiction_count} contradiction(s) reduced confidence")
    return {"score": score, "level": level, "factors": factors}
