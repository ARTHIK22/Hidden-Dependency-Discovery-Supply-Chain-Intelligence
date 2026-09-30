import re

COUNTRIES = ("United States", "United Kingdom", "India", "China", "Germany", "Japan", "Taiwan", "South Korea", "France", "Canada", "Mexico", "Vietnam")


def extract_country_mentions(text: str) -> list[str]:
    found = []
    for country in COUNTRIES:
        if re.search(r"(?<!\w)" + re.escape(country) + r"(?!\w)", text, re.IGNORECASE):
            found.append(country)
    return found
