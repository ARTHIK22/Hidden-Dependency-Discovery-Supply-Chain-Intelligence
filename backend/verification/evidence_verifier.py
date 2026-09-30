import hashlib


def verify_evidence(evidence) -> dict:
    content = getattr(evidence, "content", "") or ""
    if not content.strip():
        return {"valid": False, "reason": "evidence content is empty"}
    recorded_hash = getattr(evidence, "content_hash", None)
    actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if recorded_hash and recorded_hash != actual_hash:
        return {"valid": False, "reason": "content hash does not match stored content"}
    return {"valid": True, "content_hash": actual_hash}
