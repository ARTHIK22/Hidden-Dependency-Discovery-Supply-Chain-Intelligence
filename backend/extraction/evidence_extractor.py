import hashlib


def build_evidence_record(text: str, start: int, end: int, context_chars: int = 160) -> dict:
    if not 0 <= start < end <= len(text):
        raise ValueError("Evidence offsets are invalid")
    left, right = max(0, start - context_chars), min(len(text), end + context_chars)
    snippet = text[left:right].strip()
    return {"content": snippet, "content_hash": hashlib.sha256(snippet.encode("utf-8")).hexdigest(), "start": start, "end": end}
