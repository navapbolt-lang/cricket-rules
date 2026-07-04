"""Safety Content Filter Guardrail — blocks harmful content in input and output."""

from typing import Optional
from app.models.types import SafetyResult


BLOCKED_KEYWORDS: list[str] = [
    "hack", "exploit", "malware", "virus",
    "how to cheat", "how to scam",
    "illegal betting", "match fixing",
    "abuse", "harassment",
]


def check_safety(text: str, stage: str = "input") -> SafetyResult:
    """Check text for harmful content using keyword scanning.

    Args:
        text: User input or model output to check
        stage: "input" or "output"

    Returns:
        SafetyResult indicating if text is safe
    """
    keyword_hits = _keyword_scan(text)
    if keyword_hits:
        return SafetyResult(
            is_safe=False,
            reason=f"Blocked keywords detected: {', '.join(keyword_hits)}",
        )

    return SafetyResult(is_safe=True)


def _keyword_scan(text: str) -> list[str]:
    """Quick keyword-based scan for obvious blocked content."""
    text_lower = text.lower()
    hits = []
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            hits.append(keyword)
    return hits


def get_gemini_safety_settings() -> list[dict]:
    """Return Gemini SafetySettings for content filtering.

    Blocks HARASSMENT, HATE_SPEECH, SEXUALLY_EXPLICIT, DANGEROUS_CONTENT
    at the BLOCK_MEDIUM_AND_ABOVE threshold.
    """
    return [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
    ]
