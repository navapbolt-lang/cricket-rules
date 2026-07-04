"""Format Consistency Guardrail — ensures the response matches the detected format."""

import re
from typing import Optional
from app.models.types import Format, LawChunk, FormatResult


FORMAT_KEYWORDS = {
    Format.TEST: ["test", "test match", "test cricket", "5-day", "five-day", "red ball"],
    Format.ODI: ["odi", "one-day", "one day", "50-over", "world cup"],
    Format.T20I: ["t20", "t20i", "twenty20", "20-over", "ipl"],
}


def check_format_consistency(
    response: str,
    detected_format: Optional[Format],
    chunks: list[LawChunk],
) -> FormatResult:
    """Verify response format matches the detected format.

    Args:
        response: Generated answer text
        detected_format: Format detected from query
        chunks: Retrieved law chunks

    Returns:
        FormatResult with consistency status
    """
    if not detected_format or detected_format == Format.ALL:
        return FormatResult(is_consistent=True, mismatches=[])

    mentioned = extract_format_references(response)
    mismatches = []

    for fmt_name in mentioned:
        for fmt, keywords in FORMAT_KEYWORDS.items():
            if fmt == detected_format:
                continue
            if fmt_name in keywords or fmt_name == fmt.value:
                mismatches.append(fmt.value)

    chunk_format_ok = True
    if chunks:
        for chunk in chunks:
            fmts = [f.value for f in chunk.metadata.formats]
            if detected_format.value not in fmts and "all" not in fmts:
                chunk_format_ok = False
                break

    is_consistent = len(mismatches) == 0
    note = None
    if mismatches and detected_format:
        note = f"Answer mentions {', '.join(set(mismatches))} but query was about {detected_format.value}"

    return FormatResult(
        is_consistent=is_consistent,
        mismatches=list(set(mismatches)),
        note=note,
    )


def extract_format_references(text: str) -> list[str]:
    """Extract format-related words from text."""
    text_lower = text.lower()
    found = []
    for fmt, keywords in FORMAT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                found.append(kw)
                break
    return found
