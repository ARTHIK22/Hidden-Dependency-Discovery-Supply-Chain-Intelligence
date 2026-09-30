from collections.abc import Mapping


def score_risk(factors: Mapping[str, float], weights: Mapping[str, float] | None = None) -> dict:
    """Compute a bounded explainable weighted mean; missing factors are omitted."""
    if not factors:
        return {"score": 0.0, "severity": "low", "factors": []}
    default_weights = {key: 1.0 for key in factors}
    selected_weights = dict(weights or default_weights)
    numerator = denominator = 0.0
    explanations = []
    for name, value in factors.items():
        if not 0 <= float(value) <= 1:
            raise ValueError(f"Risk factor {name} must be between 0 and 1")
        weight = float(selected_weights.get(name, 1.0))
        if weight < 0:
            raise ValueError("Risk factor weights cannot be negative")
        numerator += float(value) * weight
        denominator += weight
        explanations.append({"name": name, "value": float(value), "weight": weight})
    score = round(numerator / denominator, 4) if denominator else 0.0
    severity = "critical" if score >= 0.85 else "high" if score >= 0.7 else "medium" if score >= 0.4 else "low"
    return {"score": score, "severity": severity, "factors": explanations}
