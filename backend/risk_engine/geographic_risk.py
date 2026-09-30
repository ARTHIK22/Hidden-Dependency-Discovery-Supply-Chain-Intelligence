from collections import defaultdict


def analyze_geographic_concentration(entity_countries: dict[str, str | None], min_entities: int = 2) -> list[dict]:
    countries: dict[str, list[str]] = defaultdict(list)
    for entity_id, country in entity_countries.items():
        if country and country.strip():
            countries[country.strip().upper()].append(entity_id)
    total = sum(len(ids) for ids in countries.values())
    return [
        {"category": "geographic_concentration", "country_code": country, "affected_entities": sorted(ids), "score": round(len(ids) / total, 4) if total else 0.0, "severity": "high" if len(ids) / total >= 0.5 else "medium", "explanation": f"{len(ids)} recorded entities are located in {country}; this is concentration, not a threat assessment."}
        for country, ids in sorted(countries.items()) if len(ids) >= min_entities and total
    ]
