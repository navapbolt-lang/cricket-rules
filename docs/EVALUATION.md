# Evaluation Strategy

## Why Evaluate?

You need to prove to B2B partners that the chatbot is accurate. Evaluation provides:
- Quantified accuracy metrics (for sales pitches)
- Regression detection (new PDFs don't break old answers)
- Systematic improvement tracking

---

## Evaluation Dataset

**File:** `data/evaluation/scenarios.json`

Each entry:
```json
{
  "id": "lbw-001",
  "category": "lbw",
  "query": "Ball pitched outside leg, hit in front, no bat, going on to hit off stump",
  "expected_answer": "NOT OUT — ball pitched outside leg. Per Law 36.1, this is automatic not out regardless of other conditions.",
  "expected_citations": ["36.1"],
  "expected_verdict": "NOT OUT",
  "format": "test",
  "difficulty": "easy"
}
```

Target: **50+ scenarios** covering:
- 10 easy (direct law lookups)
- 20 medium (two-condition scenarios)
- 20 hard (multi-condition, edge cases, format-specific)

---

## Metrics (RAGAS-based)

### 1. Faithfulness
**What it measures:** Are the claims in the answer supported by the retrieved context?

Score: 0.0 - 1.0. Target: > 0.95

### 2. Answer Relevancy
**What it measures:** Is the answer relevant to the question?

Score: 0.0 - 1.0. Target: > 0.90

### 3. Citation Accuracy
**What it measures:** What percentage of cited law numbers are correct?

```
Citation Accuracy = (correctly cited laws) / (total cited laws)
```
Target: > 0.98

### 4. Verdict Accuracy
**What it measures:** For scenario queries, is the final OUT/NOT OUT/decision correct?

```
Verdict Accuracy = (correct verdicts) / (total scenarios)
```
Target: > 0.95

### 5. Hallucination Rate
**What it measures:** What percentage of responses contain unsupported claims?

```
Hallucination Rate = (responses with at least one unsupported claim) / (total responses)
```
Target: < 0.02

---

## Running Evaluation

```bash
python scripts/run_evaluation.py

# Output:
# ┌────────────────┬────────┐
# │ Metric         │ Score  │
# ├────────────────┼────────┤
# │ Faithfulness   │ 0.97   │
# │ Answer Relev   │ 0.93   │
# │ Citation Acc   │ 0.99   │
# │ Verdict Acc    │ 0.96   │
# │ Hallucination  │ 0.01   │
# └────────────────┴────────┘
```

Results are saved to `data/evaluation/results/` with timestamps for tracking over time.

---

## Evaluation Notebook

`notebooks/evaluation.ipynb` provides:
- Visual charts for each metric
- Confusion matrix for verdict accuracy
- Per-category breakdown (LBW vs DRS vs No-ball)
- Failure case analysis (which scenarios failed and why)
