from urllib.parse import urlparse


def verify_source(source) -> dict:
    """Validate stored source metadata; this does not claim the URL was fetched."""
    reliability = float(getattr(source, "reliability_score", 0.0) or 0.0)
    if not 0 <= reliability <= 1:
        return {"valid": False, "reason": "reliability_score must be in [0, 1]"}
    url = getattr(source, "url", None)
    if url:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return {"valid": False, "reason": "source URL must be an absolute HTTP(S) URL without credentials"}
    return {"valid": True, "reliability_score": reliability, "accessed": False}
