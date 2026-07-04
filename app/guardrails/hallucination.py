"""Hallucination Detection Guardrail — verifies atomic claims against retrieved context."""

import re
from typing import Optional
from app.config import settings
from app.models.types import HallucinationResult
from app.agent.llm_client import generate_text


VERIFICATION_PROMPT = """You are a fact-checker. Determine if the following CLAIM is supported by the CONTEXT.

CONTEXT:
{context}

CLAIM: {claim}

Answer with exactly one word: SUPPORTED or UNSUPPORTED or UNCERTAIN"""


def check_factual_consistency(response: str, context: str) -> HallucinationResult:
    """Check each claim in the response against the retrieved context."""
    claims = extract_atomic_claims(response)
    failed_claims = []

    for claim in claims:
        try:
            prompt = VERIFICATION_PROMPT.format(context=context[:3000], claim=claim)
            response_text = generate_text(prompt, temperature=0.0, max_tokens=200).upper()

            if "UNSUPPORTED" in response_text:
                failed_claims.append(claim)
        except Exception:
            failed_claims.append(claim)

    return HallucinationResult(
        is_consistent=len(failed_claims) == 0,
        total_claims=len(claims),
        failed_claims=failed_claims,
    )


def extract_atomic_claims(response: str) -> list[str]:
    """Split response into individual factual claims by sentence."""
    sentences = re.split(r'(?<=[.!?])\s+', response)
    claims = []
    for s in sentences:
        cleaned = s.strip()
        if cleaned and len(cleaned) > 10:
            claims.append(cleaned)
    return claims



