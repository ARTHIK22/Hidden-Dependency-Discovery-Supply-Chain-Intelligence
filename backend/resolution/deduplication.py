from itertools import combinations

from resolution.canonicalizer import canonicalize_name
from resolution.similarity import name_similarity


def find_duplicate_candidates(entities: list, threshold: float = 0.8) -> list[dict]:
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    pairs = []
    for left, right in combinations(entities, 2):
        left_id, right_id = str(getattr(left, "id", "")), str(getattr(right, "id", ""))
        left_name = getattr(left, "canonical_name", None) or getattr(left, "name", str(left))
        right_name = getattr(right, "canonical_name", None) or getattr(right, "name", str(right))
        left_reg = getattr(left, "registration_number", None)
        right_reg = getattr(right, "registration_number", None)
        score = 1.0 if left_reg and right_reg and left_reg.casefold() == right_reg.casefold() else name_similarity(left_name, right_name)
        if getattr(left, "country", None) and getattr(right, "country", None) and left.country.casefold() != right.country.casefold():
            score = max(0.0, score - 0.15)
        if score >= threshold:
            pairs.append({"left_id": left_id, "right_id": right_id, "score": round(score, 4), "decision": "review_required", "canonical_names_equal": canonicalize_name(left_name) == canonicalize_name(right_name)})
    return sorted(pairs, key=lambda pair: -pair["score"])
