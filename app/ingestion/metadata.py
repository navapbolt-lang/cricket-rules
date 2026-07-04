"""Metadata extraction from cricket law text.

Detects format(s) from text (Test/ODI/T20I), authority (ICC vs MCC),
year/effective_date, and law title from headings.
"""

import re
from app.models.types import Format, Authority


FORMAT_PATTERNS = {
    "TEST": Format.TEST,
    "ONE-DAY": Format.ODI,
    "TWENTY20": Format.T20I,
    "ALL": Format.ALL,
}


def detect_formats(text: str) -> list[Format]:
    """Detect which cricket formats a chunk applies to.

    Searches for format keywords in text and returns matching Format enum values.
    Defaults to ALL if not specified.
    """

    formats = []
    if "TEST" in text:
        formats.append(Format.TEST)
    if "ONE-DAY" in text:
        formats.append(Format.ODI)
    if "TWENTY20" in text:
        formats.append(Format.T20I)
    if not formats:
        formats.append(Format.ALL)
    return formats


def detect_authority(text: str) -> Authority:
    """Detect whether text is from ICC or MCC source.

    Checks for 'MCC'/'Marylebone' → MCC, 'ICC'/'International Cricket Council' → ICC.
    Defaults to ICC.
    """
    if "MCC" in text or "Marylebone" in text:
        return Authority.MCC
    else:
        return Authority.ICC


def extract_law_title(text: str) -> str:
    """Extract law title from heading line like '36. LBW'."""
    for pattern in [
        r'^(\d+)\.\s+(.+?)$',
        r'^(\d+\.\d+)\s+(.+?)$',
        r'^Law\s+(\d+)\s*[-–—]\s*(.+?)$',
        r'^(\d+)\s+[-–—]\s+(.+?)$',
    ]:
        m = re.search(pattern, text, re.MULTILINE)
        if m:
            return m.group(2).strip()
    for line in text.split("\n")[:3]:
        stripped = line.strip()
        if stripped.isupper() and len(stripped) > 3:
            return stripped.title()
    return ""


def detect_year(text: str) -> int:
    """Detect year from PDF cover or header.

    Searches for '20XX' patterns and returns the most recent year found.
    Defaults to 2025 if none found.
    """
    year = re.search(r'(\d{4})', text)
    if year:
        return int(year.group(1))
    return 2025


def detect_gender(text: str) -> str:
    """Detect gender from text content or filename."""
    upper = text.upper()
    has_women = bool(re.search(r'\bWOMEN\b', upper))
    has_men = bool(re.search(r'\bMEN\b', upper))
    
    if has_women and not has_men:
        return "women"
    if has_men and not has_women:
        return "men"
    return "all"
