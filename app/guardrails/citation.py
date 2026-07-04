"""Citation Grounding Guardrail — verifies every cited law number exists in retrieved chunks."""

import re
from app.models.types import LawChunk, CitationResult

LAW_REFERENCE_PATTERN = r'Law\s+(\d+(?:\.\d+)*)'


def verify_citations(response: str, chunks: list[LawChunk]) -> CitationResult:
    """Verify all law citations in the response are valid and supported.

    Steps:
    1. Extract all "Law X.Y" references from response text
    2. Check each law_number exists in chunk metadata
    3. For valid citations, check the surrounding claim is supported

    Args:
        response: The generated answer text
        chunks: The retrieved law chunks used as context

    Returns:
        CitationResult with validation status
    """
    cited_laws = extract_law_references(response)
    if not cited_laws:
        return CitationResult(
            all_valid=True,
            invalid_citations=[],
            unsupported_claims=[],
        )

    chunk_law_numbers = set()
    for c in chunks:
        chunk_law_numbers.add(c.metadata.law_number)
        chunk_law_numbers.add(c.metadata.parent_law)

    invalid_laws = []
    for law in cited_laws:
        if law in chunk_law_numbers:
            continue
        if any(law.startswith(c) or c.startswith(law) for c in chunk_law_numbers if "." in law or "." in c):
            continue
        invalid_laws.append(law)
    unsupported = check_claim_support(response, chunks)

    is_valid = len(invalid_laws) == 0 and len(unsupported) == 0

    return CitationResult(
        all_valid=is_valid,
        invalid_citations=invalid_laws,
        unsupported_claims=unsupported,
    )


def extract_law_references(text: str) -> list[str]:
    """Extract law number references from text.

    Matches patterns like "Law 36.1", "Law 36", "Laws 36.1-36.3".
    """
    matches = re.findall(LAW_REFERENCE_PATTERN, text)
    seen = set()
    unique = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            unique.append(m)
    return unique


def check_claim_support(response: str, chunks: list[LawChunk]) -> list[dict]:
    """Check that each claim referencing a law is supported by chunk text.

    For each cited law, check if the sentence containing it has
    keywords that appear in the corresponding chunk text.
    """
    sentences = re.split(r'(?<=[.!?])\s+', response)
    unsupported = []

    chunk_text_by_law: dict[str, str] = {}
    for c in chunks:
        chunk_text_by_law[c.metadata.law_number] = c.text

    for sentence in sentences:
        law_refs = re.findall(LAW_REFERENCE_PATTERN, sentence)
        for law in law_refs:
            if law in chunk_text_by_law:
                chunk_words = set(chunk_text_by_law[law].lower().split())
                sentence_keywords = set(
                    w.lower() for w in sentence.split()
                    if len(w) > 4 and not w.startswith("law")
                )
                if sentence_keywords and len(sentence_keywords) >= 3:
                    overlap = sentence_keywords & chunk_words
                    if len(overlap) < max(1, len(sentence_keywords) * 0.25):
                        unsupported.append({
                            "law": law,
                            "claim": sentence,
                            "support_fraction": len(overlap) / max(len(sentence_keywords), 1),
                        })

    return unsupported
