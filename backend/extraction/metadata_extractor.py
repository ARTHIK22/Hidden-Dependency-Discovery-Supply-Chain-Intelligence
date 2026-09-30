import re
from datetime import date

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
DATE_PATTERN = re.compile(r"\b(20\d{2})-(0[1-9]|1[0-2])-([0-2]\d|3[01])\b")


def extract_metadata(text: str) -> dict:
    urls = [match.group(0).rstrip(".,);]") for match in URL_PATTERN.finditer(text)]
    dates = []
    for match in DATE_PATTERN.finditer(text):
        try:
            dates.append(date.fromisoformat(match.group(0)).isoformat())
        except ValueError:
            continue
    return {"urls": list(dict.fromkeys(urls)), "dates": list(dict.fromkeys(dates))}
