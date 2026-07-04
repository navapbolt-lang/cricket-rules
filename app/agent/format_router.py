"""Format and gender detection from user query text."""

from typing import Optional
from app.models.types import Format, Gender


FORMAT_KEYWORDS: dict[Format, list[str]] = {
    Format.TEST: [
        "test", "test match", "test cricket", "test matches",
        "5-day", "five-day", "five day", "red ball",
        "ashes", "border-gavaskar",
    ],
    Format.ODI: [
        "odi", "odis", "one-day", "one day", "one-dayer",
        "50-over", "50 over", "world cup",
        "cwc", "odi world cup",
    ],
    Format.T20I: [
        "t20", "t20i", "t20is", "twenty20", "twenty-20",
        "20-over", "20 over", "twenty over",
        "ipl", "bbl", "cpl", "psl", "sa20", "the hundred",
        "t20 world cup", "world t20",
    ],
}


def detect_format(query: str, preferred_format: Optional[Format] = None) -> Format:
    """Detect the cricket format from user query.

    Strategy:
    1. If user explicitly specified a format, use it
    2. Check query text for format keywords
    3. If multiple formats match, return the most specific one
    4. If no match, return ALL

    Args:
        query: User's question text
        preferred_format: User's explicit format choice (e.g. from UI selector)

    Returns:
        Detected Format enum
    """
    if preferred_format:
        return preferred_format

    query_lower = query.lower()
    detected = {Format.TEST: False, Format.ODI: False, Format.T20I: False}

    for fmt, keywords in FORMAT_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                detected[fmt] = True
                break

    active = [fmt for fmt, val in detected.items() if val]

    if len(active) == 1:
        return active[0]
    if len(active) > 1:
        return Format.ALL

    return Format.ALL


def format_to_string(f: Format) -> str:
    """Convert Format enum to human-readable string."""
    mapping = {
        Format.TEST: "Test matches",
        Format.ODI: "ODIs (One-Day Internationals)",
        Format.T20I: "T20Is (Twenty20 Internationals)",
        Format.ALL: "all formats",
    }
    return mapping.get(f, "all formats")


GENDER_KEYWORDS = {
    Gender.MEN: [r"\bmen\b", r"\bmen's\b", r"\bmens\b", r"\bman\b"],
    Gender.WOMEN: [r"\bwomen\b", r"\bwomen's\b", r"\bwomens\b", r"\bwoman\b", r"\bladys?\b", r"\bshe\b", r"\bher\b"],
}


def detect_gender(query: str) -> Gender:
    """Detect gender context from user query."""
    import re
    q = query.lower()
    scored = {Gender.MEN: 0, Gender.WOMEN: 0}

    for gender, patterns in GENDER_KEYWORDS.items():
        for pat in patterns:
            if re.search(pat, q):
                scored[gender] += 1

    if scored[Gender.WOMEN] > scored[Gender.MEN]:
        return Gender.WOMEN
    if scored[Gender.MEN] > scored[Gender.WOMEN]:
        return Gender.MEN
    return Gender.ALL
