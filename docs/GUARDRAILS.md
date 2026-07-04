# Guardrails — Safety & Accuracy Layer

## Why Guardrails?

LLMs hallucinate. They invent law numbers, misinterpret conditions, and mix up formats. Guardrails are the **enforcement layer** that catches these failures before the user sees them.

---

## Pipeline (sequential — all must pass)

```
Response from LLM
        │
        ▼
┌────────────────────┐
│ 1. Citation        │  ← Does every cited law number exist
│    Grounding       │    in the retrieved chunks?
└────────┬───────────┘
         │ FAIL → regenerate
         ▼
┌────────────────────┐
│ 2. Hallucination   │  ← Is every claim supported by
│    Detection       │    the retrieved context?
└────────┬───────────┘
         │ FAIL → safe refusal
         ▼
┌────────────────────┐
│ 3. Format          │  ← Does the answer match the
│    Consistency     │    detected format? (e.g., using ODI
│                    │    rules when user asked about Test)
└────────┬───────────┘
         │ FAIL → append correction + regenerate if severe
         ▼
┌────────────────────┐
│ 4. Confidence Gate │  ← Is the retrieval confidence
│                    │    above threshold (0.7)?
└────────┬───────────┘
         │ FAIL → safe refusal ("I'm not confident")
         ▼
┌────────────────────┐
│ 5. Safety Filter   │  ← Input & output content filtering
│                    │    (abuse, hate, illegal content)
└────────┬───────────┘
         │ FAIL → block
         ▼
    Serve to user
```

---

## Guardrail 1: Citation Grounding

**File:** `app/guardrails/citation.py`

**Purpose:** Verify that every law number mentioned in the response actually exists in the retrieved chunks.

**Logic:**
```python
def verify_citations(response: str, chunks: list[LawChunk]) -> CitationResult:
    # 1. Extract all "Law X.Y" or "Law X" patterns from response
    cited_laws = extract_law_references(response)
    # 2. Check each law exists in chunk metadata
    valid_laws = [c for c in cited_laws if c in chunk_law_numbers]
    invalid_laws = [c for c in cited_laws if c not in chunk_law_numbers]
    # 3. For each valid law, check the claim is supported by the chunk text
    unsupported_claims = check_claim_support(response, chunks)
    # 4. Return result
    return CitationResult(
        all_valid=(len(invalid_laws) == 0 and len(unsupported_claims) == 0),
        invalid_citations=invalid_laws,
        unsupported_claims=unsupported_claims
    )
```

**Behavior on failure:**
- Invalid citations found → **regenerate the response**
- Unsupported claims found → **regenerate the response**
- If regeneration also fails → safe refusal

---

## Guardrail 2: Hallucination Detection

**File:** `app/guardrails/hallucination.py`

**Purpose:** Verify that each factual claim in the response is supported by the retrieved context.

**Logic:**
```python
def check_factual_consistency(response: str, context: str) -> HallucinationResult:
    # 1. Split response into atomic claims (by sentences + citations)
    claims = extract_atomic_claims(response)
    # 2. For each claim, ask Gemini Flash:
    #    "Is this claim supported by the context? Answer YES/NO."
    results = []
    for claim in claims:
        verdict = verify_claim(claim, context)
        results.append(verdict)
    # 3. Return result
    return HallucinationResult(
        is_consistent=all(r.consistent for r in results),
        failed_claims=[r for r in results if not r.consistent]
    )
```

**Behavior on failure:**
- Any claim unsupported → safe refusal with message:
  *"I cannot verify this answer with confidence. Please rephrase or ask a different question."*

---

## Guardrail 3: Format Consistency

**File:** `app/guardrails/format_check.py`

**Purpose:** Ensure the response doesn't use rules from the wrong format.

**Logic:**
```python
def check_format_consistency(
    response: str,
    detected_format: Format,
    chunks: list[LawChunk]
) -> FormatResult:
    # 1. Detect which formats are mentioned in the response
    mentioned_formats = extract_format_references(response)
    # 2. If response mentions a format different from detected_format, flag it
    mismatches = [f for f in mentioned_formats if f != detected_format 
                  and f != Format.ALL]
    # 3. Check that chunks used match the detected format
    chunk_format_mismatch = any(
        detected_format not in c.metadata.formats 
        and Format.ALL not in c.metadata.formats
        for c in chunks
    )
    return FormatResult(
        is_consistent=(len(mismatches) == 0 and not chunk_format_mismatch),
        mismatches=mismatches,
        note="Answer uses Test rules but query was about ODI" if mismatches else None
    )
```

**Behavior on failure:**
- Minor mismatch → append correction note to answer
- Major mismatch → regenerate with format explicitly specified

---

## Guardrail 4: Confidence Gate

**File:** `app/guardrails/confidence.py`

**Purpose:** Reject answers where the retrieval confidence is too low.

**Logic:**
```python
def should_serve_response(
    retrieval_scores: list[float],
    guardrail_results: list[GuardrailResult]
) -> bool:
    # 1. Check max similarity score
    max_score = max(retrieval_scores) if retrieval_scores else 0
    
    # 2. If score < 0.7 AND citation check failed → reject
    if max_score < 0.7:
        # Check if citation guardrail caught this
        if any(not r.passed for r in guardrail_results 
               if r.name == "citation"):
            return False
    
    # 3. If hallucination guardrail failed → always reject
    if any(not r.passed for r in guardrail_results 
           if r.name == "hallucination"):
        return False
    
    # 4. Otherwise pass
    return True
```

**Behavior on failure:** Return:
```json
{
  "answer": "I'm not confident enough to answer this accurately. Could you rephrase the question or specify a law number?",
  "citations": [],
  "confidence": 0.0,
  "suggested_questions": [...],
  "format_used": null,
  "guardrail_status": "low_confidence"
}
```

---

## Guardrail 5: Safety Filter

**File:** `app/guardrails/safety.py`

**Purpose:** Block harmful content in both input and output.

**Logic:**
```python
def check_safety(text: str, stage: str = "input") -> SafetyResult:
    # 1. Check against blocked categories:
    #    - Violence, hate speech, harassment
    #    - Illegal activity
    #    - Sexual content
    #    - Spam or commercial solicitation
    # 2. Use Gemini SafetySettings or a smaller classifier
    # 3. Return result
```

**Behavior on failure:**
- Input blocked → return *"I can only answer cricket rules questions."*
- Output blocked → suppress and regenerate

---

## Monitoring Guardrail Performance

Every guardrail result is logged with the query for analysis:

```json
{
  "query": "...",
  "guardrails": {
    "citation": {"passed": true, "invalid": [], "unsupported": []},
    "hallucination": {"passed": true, "failed_claims": 0},
    "format_check": {"passed": true, "mismatches": []},
    "confidence": 0.94,
    "safety": {"passed": true}
  },
  "served": true
}
```

This lets you:
- Track guardrail pass rates over time
- Identify which guardrails fire most often
- Improve retrieval/chunking for common failure modes
