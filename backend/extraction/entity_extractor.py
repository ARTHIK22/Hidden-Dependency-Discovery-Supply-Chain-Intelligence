import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EntityMention:
    name: str
    start: int
    end: int


def extract_known_entity_mentions(text: str, known_names: list[str]) -> list[EntityMention]:
    """Match only supplied names/aliases; this is deterministic string matching, not open-domain NER."""
    names = sorted({name.strip() for name in known_names if name and name.strip()}, key=len, reverse=True)
    if not names:
        return []
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(name) for name in names) + r")(?!\w)", re.IGNORECASE)
    mentions = [EntityMention(match.group(0), match.start(), match.end()) for match in pattern.finditer(text)]
    return [item for item in mentions if not any(other.start <= item.start and item.end <= other.end and other != item for other in mentions)]
