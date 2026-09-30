from verification.confidence_engine import calculate_confidence
from verification.contradiction_detector import detect_contradictions
from verification.evidence_verifier import verify_evidence
from verification.source_verifier import verify_source


def verify_relationship_claim(evidence_items: list, source_by_id: dict) -> dict:
    valid_evidence = []
    reliabilities = []
    evidence_confidences = []
    texts = []
    source_ids = set()
    for evidence in evidence_items:
        validation = verify_evidence(evidence)
        if not validation["valid"]:
            continue
        valid_evidence.append(evidence)
        evidence_confidences.append(float(getattr(evidence, "confidence_score", 0.0) or 0.0))
        texts.append(getattr(evidence, "content", ""))
        source = source_by_id.get(getattr(evidence, "source_id", None))
        if source is not None:
            source_check = verify_source(source)
            if source_check["valid"]:
                reliabilities.append(source_check["reliability_score"])
                source_ids.add(str(getattr(source, "id", "")))
    contradictions = detect_contradictions(texts)
    confidence = calculate_confidence(source_reliabilities=reliabilities, evidence_confidences=evidence_confidences, contradiction_count=len(contradictions))
    high_quality_single_source = len(reliabilities) == 1 and reliabilities[0] >= 0.9 and evidence_confidences and evidence_confidences[0] >= 0.85
    verified = bool(valid_evidence and not contradictions and (len(source_ids) >= 2 or high_quality_single_source) and confidence["score"] >= 0.75)
    return {"verified": verified, "status": "contradicted" if contradictions else "verified" if verified else "unverified", "confidence": confidence, "valid_evidence_count": len(valid_evidence), "source_count": len(source_ids), "contradictions": contradictions}
