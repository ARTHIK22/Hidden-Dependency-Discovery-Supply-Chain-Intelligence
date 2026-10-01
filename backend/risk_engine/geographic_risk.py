"""Geographic concentration based only on recorded jurisdiction values."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable


def geographic_concentration(jurisdictions: Iterable[str | None]) -> tuple[float | None, str]:
    known = [value.strip().casefold() for value in jurisdictions if value and value.strip()]
    if not known:
        return None, "No verified dependency has a recorded jurisdiction."
    counts = Counter(known)
    region, count = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
    score = 100.0 * count / len(known)
    return round(score, 2), f"{count} of {len(known)} jurisdiction-tagged dependencies share recorded jurisdiction '{region}'."
