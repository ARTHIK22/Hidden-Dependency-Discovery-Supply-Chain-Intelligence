from difflib import SequenceMatcher

from resolution.canonicalizer import canonicalize_name


def name_similarity(left: str, right: str) -> float:
    """Return deterministic lexical similarity in [0, 1] for triage only."""
    a, b = canonicalize_name(left), canonicalize_name(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()
