import re
import unicodedata

LEGAL_SUFFIXES = {"inc", "incorporated", "corp", "corporation", "ltd", "limited", "llc", "plc", "pvt", "private", "co", "company"}


def canonicalize_name(name: str) -> str:
    """Normalize a name for candidate matching; never implies entities are equal."""
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").casefold()
    value = re.sub(r"\b(?:[a-z]\.){2,}[a-z]?\.?", lambda match: match.group(0).replace(".", ""), value)
    tokens = re.findall(r"[a-z0-9]+", value)
    while tokens and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)
