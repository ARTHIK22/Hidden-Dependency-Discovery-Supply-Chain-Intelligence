import re

POSITIVE_TERMS = {"supplies", "supply", "provides", "manufactures", "owns", "operates", "uses", "active"}
NEGATIVE_TERMS = {"stopped", "terminated", "no longer", "ceased", "does not", "did not", "former", "ended"}


def detect_contradictions(claim_texts: list[str]) -> list[dict]:
    """Detect opposing assertion cues in analyst-provided evidence text."""
    normalized = [re.sub(r"\s+", " ", text.casefold()).strip() for text in claim_texts]
    positive = [i for i, text in enumerate(normalized) if any(term in text.split() for term in POSITIVE_TERMS)]
    negative = [i for i, text in enumerate(normalized) if any(term in text for term in NEGATIVE_TERMS)]
    if positive and negative:
        return [{"type": "polarity_conflict", "positive_evidence_indexes": positive, "negative_evidence_indexes": negative, "explanation": "Evidence contains both an active-relationship cue and a cessation/negation cue; analyst review is required."}]
    return []
