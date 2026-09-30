import re

VERBS = {
    "supplies": "SUPPLIES", "supply": "SUPPLIES", "provides": "PROVIDES",
    "manufactures": "MANUFACTURES", "owns": "OWNS", "operates": "OPERATES",
    "distributes": "DISTRIBUTES", "uses": "USES", "depends on": "DEPENDS_ON",
}


def extract_relationship_candidates(text: str, known_names: list[str]) -> list[dict]:
    """Extract candidate edges only when both endpoints are known canonical names/aliases."""
    if len(known_names) < 2:
        return []
    names = sorted({name.strip() for name in known_names if name and name.strip()}, key=len, reverse=True)
    name_group = "(?:" + "|".join(re.escape(name) for name in names) + ")"
    verb_group = "|".join(sorted((re.escape(verb) for verb in VERBS), key=len, reverse=True))
    pattern = re.compile(rf"(?<!\w)(?P<source>{name_group})\s+(?P<verb>{verb_group})\s+(?P<target>{name_group})(?!\w)", re.IGNORECASE)
    candidates = []
    for match in pattern.finditer(text):
        source = next((name for name in names if name.casefold() == match.group("source").casefold()), match.group("source"))
        target = next((name for name in names if name.casefold() == match.group("target").casefold()), match.group("target"))
        if source.casefold() == target.casefold():
            continue
        verb = re.sub(r"\s+", " ", match.group("verb").casefold())
        candidates.append({"source_name": source, "target_name": target, "relationship_type": VERBS[verb], "confidence": 0.65, "evidence_text": match.group(0), "start": match.start(), "end": match.end(), "verification_status": "candidate"})
    return candidates
