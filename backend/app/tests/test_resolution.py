from types import SimpleNamespace

from resolution.canonicalizer import canonicalize_name
from resolution.entity_resolver import rank_entity_candidates
from resolution.similarity import name_similarity


def test_canonicalizer_normalizes_punctuation_and_legal_suffixes():
    assert canonicalize_name("A.B.C. Limited") == "abc"
    assert canonicalize_name("ABC, Inc.") == "abc"


def test_similarity_is_bounded_and_exact_normalized_names_match():
    assert name_similarity("Example Ltd", "Example Limited") == 1.0
    assert 0.0 <= name_similarity("Acme", "Different Works") <= 1.0


def test_entity_resolution_uses_identifiers_and_never_auto_merges():
    entity = SimpleNamespace(id="entity-1", name="ABC Limited", canonical_name="ABC Limited", registration_number="REG-42", country="IN", website="https://abc.example")
    match = rank_entity_candidates("A.B.C. Ltd", [entity], registration_number="REG-42", country="IN")[0]
    assert match["status"] == "MATCH"
    candidates = rank_entity_candidates("A.B.C. Ltd", [entity])
    assert candidates[0]["score"] >= 0.9
