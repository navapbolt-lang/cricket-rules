"""Tests for guardrail checks."""

import pytest
from app.guardrails.citation import verify_citations, extract_law_references
from app.guardrails.format_check import check_format_consistency, extract_format_references
from app.guardrails.confidence import should_serve_response, get_safe_refusal_response
from app.guardrails.safety import check_safety
from app.models.types import Format, GuardrailResult, GuardrailName


class TestCitationGrounding:
    def test_valid_citations_pass(self, sample_chunks):
        response = "The batsman is out LBW per Law 36.1."
        result = verify_citations(response, sample_chunks)
        assert result.all_valid is True

    def test_invalid_citations_fail(self, sample_chunks):
        response = "Per Law 99.99, this is not out."
        result = verify_citations(response, sample_chunks)
        assert result.all_valid is False
        assert "99.99" in result.invalid_citations

    def test_no_citations_no_chunks(self):
        response = "The batsman is out."
        result = verify_citations(response, [])
        assert result.all_valid is True

    def test_extract_law_references(self):
        text = "Law 36.1 applies. Law 36.2 and Law 41 also apply."
        refs = extract_law_references(text)
        assert "36.1" in refs
        assert "36.2" in refs
        assert "41" in refs


class TestFormatCheck:
    def test_matching_format_passes(self, sample_chunks):
        result = check_format_consistency(
            "In Test matches, this is out.",
            Format.TEST,
            sample_chunks,
        )
        assert result.is_consistent is True

    def test_wrong_format_fails(self, sample_chunks):
        result = check_format_consistency(
            "In T20Is, this rule changes completely.",
            Format.TEST,
            [],
        )
        assert result.is_consistent is False or len(result.mismatches) > 0

    def test_all_format_always_passes(self, sample_chunks):
        result = check_format_consistency(
            "This law applies to all formats.",
            Format.ALL,
            sample_chunks,
        )
        assert result.is_consistent is True


class TestConfidenceGate:
    def test_high_confidence_passes(self):
        results = [
            GuardrailResult(name=GuardrailName.HALLUCINATION, passed=True, details=None),
            GuardrailResult(name=GuardrailName.CITATION, passed=True, details=None),
            GuardrailResult(name=GuardrailName.SAFETY, passed=True, details=None),
            GuardrailResult(name=GuardrailName.FORMAT_CHECK, passed=True, details=None),
        ]
        assert should_serve_response(0.85, results) is True

    def test_hallucination_fail_rejected(self):
        results = [
            GuardrailResult(name=GuardrailName.HALLUCINATION, passed=False, details=None),
        ]
        assert should_serve_response(0.85, results) is False

    def test_safety_fail_rejected(self):
        results = [
            GuardrailResult(name=GuardrailName.HALLUCINATION, passed=True, details=None),
            GuardrailResult(name=GuardrailName.SAFETY, passed=False, details=None),
        ]
        assert should_serve_response(0.85, results) is False

    def test_low_confidence_and_bad_citation_rejected(self):
        results = [
            GuardrailResult(name=GuardrailName.HALLUCINATION, passed=True, details=None),
            GuardrailResult(name=GuardrailName.CITATION, passed=False, details=None),
        ]
        assert should_serve_response(0.3, results) is False

    def test_safe_refusal_has_low_confidence(self):
        refusal = get_safe_refusal_response()
        assert refusal["confidence"] == 0.0
        assert "guardrail_status" in refusal


class TestSafetyFilter:
    def test_safe_input_passes(self):
        result = check_safety("What is the LBW rule?")
        assert result.is_safe is True

    def test_blocked_input_fails(self):
        result = check_safety("How to hack the system?")
        assert result.is_safe is False

    def test_blocked_keyword_returns_reason(self):
        result = check_safety("match fixing tips")
        assert result.is_safe is False
        assert result.reason is not None
