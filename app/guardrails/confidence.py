"""Confidence Gate Guardrail — rejects answers when retrieval scores or guardrail results are insufficient."""

from app.models.types import GuardrailResult, GuardrailName

CONFIDENCE_THRESHOLD = 0.3


def should_serve_response(
    max_similarity_score: float,
    guardrail_results: list[GuardrailResult],
) -> bool:
    """Decide whether to serve the response or reject it.

    Rules:
    - If hallucination check fails → ALWAYS reject
    - If max similarity < 0.7 AND citation check fails → reject
    - If any guardrail result is explicitly failed → reject
    - Otherwise → serve

    Args:
        max_similarity_score: Highest retrieval score from search
        guardrail_results: Results from all guardrail checks

    Returns:
        True if response should be served, False otherwise
    """
    result_map = {r.name: r for r in guardrail_results}

    hallucination = result_map.get(GuardrailName.HALLUCINATION)
    if hallucination and not hallucination.passed:
        return False

    citation = result_map.get(GuardrailName.CITATION)
    if max_similarity_score < CONFIDENCE_THRESHOLD and citation and not citation.passed:
        return False

    safety = result_map.get(GuardrailName.SAFETY)
    if safety and not safety.passed:
        return False

    format_check = result_map.get(GuardrailName.FORMAT_CHECK)
    if format_check:
        pass

    return True


def get_safe_refusal_response() -> dict:
    """Return a safe refusal message when confidence is too low."""
    return {
        "answer": "I'm not confident enough to answer this accurately. Could you rephrase the question or specify a law number? Some things you can try: mention a specific law (e.g. 'Law 36'), specify the format (Test/ODI/T20I), or describe the scenario more clearly.",
        "citations": [],
        "confidence": 0.0,
        "suggested_questions": [
            "What is the LBW law?",
            "How does DRS work?",
            "What is a no-ball?",
        ],
        "format_used": None,
        "guardrail_status": "low_confidence",
    }
