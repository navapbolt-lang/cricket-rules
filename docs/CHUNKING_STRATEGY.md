# Chunking Strategy

## Goal

Split ICC Playing Conditions and MCC Laws PDFs into semantically meaningful chunks that preserve the law number hierarchy while being small enough for effective RAG retrieval.

---

## Hierarchy Detection

Cricket laws follow a strict numeric hierarchy:

```
36  ───── LBW ─────────────────────── section (major law)
├── 36.1 ── Pitching ──────────────── clause (primary chunk)
├── 36.2 ── Impact ────────────────── clause
├── 36.3 ── Trajectory ────────────── clause
│   └── 36.3.1 ── Wicket falling ──── sub-clause (optional sub-chunk)
└── 36.4 ── Bat involvement ───────── clause
```

---

## Chunking Rules

### 1. Law Number Regex

```python
# Matches "36.", "36.1", "36.1.1", "25.3", etc.
LAW_NUMBER_PATTERN = r'^(\d{1,2}(?:\.\d{1,2})*(?:\.\d{1,2})?)\s'
```

### 2. Hierarchy Rules

| Level | Pattern | Chunk Type | Target Size |
|---|---|---|---|
| Major law | `^(\d{1,2})\.$` (e.g., "36.") | Section header | ~100 tokens (heading + intro) |
| Clause | `^(\d{1,2}\.\d{1,2})\s` (e.g., "36.1") | Primary chunk | ~500 tokens |
| Sub-clause | `^(\d{1,2}\.\d{1,2}\.\d{1,2})\s` (e.g., "36.1.1") | Sub-chunk | ~300 tokens (optional) |

### 3. Content Rules

- Each primary chunk starts at a clause heading and includes all text until the next clause at the same level
- Sub-clauses are merged into their parent clause chunk (not split separately) unless they exceed 500 tokens
- Chunks have 50-token overlap with the previous chunk (last 50 tokens of chunk N = first 50 tokens of chunk N+1)

### 4. Metadata Per Chunk

```python
{
    "law_number": "36.1",
    "parent_law": "36",
    "title": "LBW — Pitching",
    "formats": ["test", "odi", "t20i"],  # Extracted from PDF intro/section headers
    "authority": "icc",  # or "mcc"
    "year": 2025,
    "effective_date": "2025-06-01",
    "page_number": 42,
    "chunk_index": 3,  # Order within the parent law
    "chunk_type": "clause"  # "section", "clause", "subclause"
}
```

---

## Format Detection Strategy

ICC Playing Conditions PDFs typically state at the start which format they apply to:

- "TEST MATCHES" → format: ["test"]
- "ONE-DAY INTERNATIONALS" → format: ["odi"]  
- "TWENTY20 INTERNATIONAL" → format: ["t20i"]
- "ALL FORMATS" → format: ["test", "odi", "t20i"]

MCC Laws apply to all formats universally.

---

## Example Output

```python
Chunk(
    id="36.1-icc-2025-03",
    text="36.1 PITCHING\n...the ball pitches in line with the stumps or on the off side...",
    metadata=ChunkMetadata(
        law_number="36.1",
        parent_law="36",
        title="LBW — Pitching",
        formats=[Format.TEST, Format.ODI, Format.T20I],
        authority=Authority.ICC,
        year=2025,
        effective_date="2025-06-01",
        page_number=42,
        chunk_index=3,
        chunk_type="clause"
    )
)
```
