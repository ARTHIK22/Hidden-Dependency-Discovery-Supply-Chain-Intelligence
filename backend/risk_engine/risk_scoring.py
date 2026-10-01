"""Shared deterministic scoring helpers and persisted factor vocabulary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class RiskFactor:
    key: str
    label: str
    status: str
    score: float | None
    explanation: str
    source: str | None = None
    evidence_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence_ids"] = list(self.evidence_ids)
        return result


@dataclass(frozen=True)
class RiskAssessment:
    target_type: str
    target_id: str
    score: float | None
    level: str
    factors: tuple[RiskFactor, ...]
    propagated_score: float | None
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "target_type": self.target_type,
            "target_id": self.target_id,
            "score": self.score,
            "level": self.level,
            "factors": [factor.as_dict() for factor in self.factors],
            "propagated_score": self.propagated_score,
            "reason": self.reason,
            "unknown_factors": [factor.key for factor in self.factors if factor.status == "UNKNOWN"],
        }


def risk_level(score: float | None, thresholds: tuple[float, float, float]) -> str:
    if score is None:
        return "UNKNOWN"
    low, medium, high = thresholds
    if score >= high:
        return "CRITICAL"
    if score >= medium:
        return "HIGH"
    if score >= low:
        return "MEDIUM"
    return "LOW"


def weighted_score(factors: Iterable[RiskFactor], weights: dict[str, float]) -> float | None:
    known = [factor for factor in factors if factor.status == "KNOWN" and factor.score is not None]
    denominator = sum(weights.get(factor.key, 0.0) for factor in known)
    if denominator <= 0:
        return None
    return round(sum(float(factor.score) * weights[factor.key] for factor in known) / denominator, 2)


def make_factor(
    key: str,
    label: str,
    score: float | None,
    explanation: str,
    *,
    source: str | None = None,
    evidence_ids: Iterable[str] = (),
) -> RiskFactor:
    if score is None:
        return RiskFactor(key, label, "UNKNOWN", None, explanation, source, tuple(sorted(set(evidence_ids))))
    normalized = min(100.0, max(0.0, float(score)))
    return RiskFactor(key, label, "KNOWN", round(normalized, 2), explanation, source, tuple(sorted(set(evidence_ids))))
