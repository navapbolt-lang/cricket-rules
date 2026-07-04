# Cricket Rules AI — Architecture Document

## 1. Project Overview

**Product:** A B2B embeddable AI chatbot that answers cricket rule questions with exact law citations. Customers (Hotstar, Cricbuzz, fantasy apps, cricket academies) embed a `<script>` tag and get a branded, context-aware rules assistant on their site.

**Goal:** Replace vague Google searches and LLM hallucinations with precise, citation-grounded cricket law answers.

---

## 2. Tech Stack

| Component | Choice | Rationale |
|---|---|---|
| **LLM** | Gemini Pro (Google AI) | Cheapest top-tier LLM, 1M context window, excellent function calling |
| **Backend** | Python 3.11+ / FastAPI | Async, performant, great DX |
| **Vector DB** | Qdrant | Native hybrid search (vector + BM25), built-in metadata filtering, free tier |
| **Embeddings** | Gemini Embedding API | Same provider as LLM — fewer API keys, lower latency |
| **Re-ranker** | BGE-reranker-v2-m3 | Local, free, runs on CPU, great cross-encoder quality |
| **PDF Parsing** | PyMuPDF (fitz) | Fastest Python PDF parser, preserves structure well |
| **Widget** | Vanilla JS + Shadow DOM | Zero dependencies, ~10KB gzipped, true CSS isolation |
| **Databases** | PostgreSQL + Redis | Partners & usage tracking (Postgres), rate limits & cache (Redis) |
| **Hosting** | Docker + Railway/Render/GCP | Portable, scalable, free tier available |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PARTNER WEBSITE                            │
│  (Hotstar / Cricbuzz / Academy Site)                               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  <script src="https://api.cricketrules.ai/widget.js"        │  │
│  │         data-partner="hotstar"                               │  │
│  │         data-brand-color="#1a1a2e"></script>                 │  │
│  └─────────────────────┬────────────────────────────────────────┘  │
│                        │                                            │
│  ┌─────────────────────▼────────────────────────────────────────┐  │
│  │  Widget (Shadow DOM)                                         │  │
│  │  - Floating button → chat sidebar                            │  │
│  │  - Auto-detects page context (match/article/general)         │  │
│  │  - Server-Sent Events for streaming answers                  │  │
│  │  - Suggested scenarios from API                              │  │
│  └─────────────────────┬────────────────────────────────────────┘  │
└────────────────────────┼────────────────────────────────────────────┘
                         │ HTTPS / SSE
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     YOUR BACKEND (api.cricketrules.ai)              │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  API LAYER (FastAPI)                                         │  │
│  │  ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐ │  │
│  │  │ POST /chat   │  │ GET /suggest   │  │ POST /chat/stream│ │  │
│  │  └──────┬───────┘  └───────┬────────┘  └────────┬─────────┘ │  │
│  │         │                  │                     │            │  │
│  │  ┌──────▼──────────────────▼─────────────────────▼────────┐  │  │
│  │  │  Middleware: Partner Auth → Rate Limit → Usage Log    │  │  │
│  │  └────────────────────────┬──────────────────────────────┘  │  │
│  └───────────────────────────┼──────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────▼──────────────────────────────────┐  │
│  │  ORCHESTRATION LAYER                                        │  │
│  │  ChatService                                                 │  │
│  │  1. Query Understanding — classify & extract entities        │  │
│  │  2. Format Detection — Test/ODI/T20I (auto or user-specified)│  │
│  │  3. Route Decision — Simple RAG or Agent based on query type│  │
│  │  4. Response Generation                                      │  │
│  └───────────────────────────┬──────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────▼──────────────────────────────────┐  │
│  │  RAG PIPELINE                ┌─────────────────────────────┐ │  │
│  │  ┌──────────────┐            │  AGENT ENGINE               │ │  │
│  │  │ Hybrid       │◄────context┤  ┌──────────────────────┐  │ │  │
│  │  │ Search       │            │  │ ReAct Loop           │  │ │  │
│  │  │ (vector +    │            │  │ (Gemini Pro tool     │  │ │  │
│  │  │  BM25)       │            │  │  calling)            │  │ │  │
│  │  └──────┬───────┘            │  └────────┬─────────────┘  │ │  │
│  │         │                    │           │                │ │  │
│  │  ┌──────▼───────┐            │  ┌────────▼─────────────┐  │ │  │
│  │  │ Re-ranker    │            │  │ Tools:               │  │ │  │
│  │  │ (cross-      │            │  │ retrieve_law()       │  │ │  │
│  │  │  encoder)    │            │  │ check_condition()    │  │ │  │
│  │  └──────┬───────┘            │  │ compare_formats()    │  │ │  │
│  │         │                    │  │ get_amendments()     │  │ │  │
│  │  ┌──────▼───────┐            │  │ get_scenario_steps() │  │ │  │
│  │  │ Context      │            │  └──────────────────────┘  │ │  │
│  │  │ Builder      │            └─────────────────────────────┘ │  │
│  │  └──────────────┘                                             │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────▼──────────────────────────────────┐  │
│  │  GUARDRAILS LAYER (applied sequentially)                    │  │
│  │  ┌────────────┐  ┌──────────────┐  ┌───────┐  ┌──────────┐  │  │
│  │  │ Citation   │→ │ Hallucination│→ │Format │→ │ Safety   │  │  │
│  │  │ Grounding  │  │ Detection    │  │Check  │  │ Filter   │  │  │
│  │  └────────────┘  └──────────────┘  └───────┘  └──────────┘  │  │
│  │  If ANY guardrail fails → regenerate or return safe refusal   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  DATA LAYER                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Qdrant          │  │  PostgreSQL      │  │  Redis           │  │
│  │  Collections:    │  │  Tables:         │  │  Usage:          │  │
│  │  icc_laws        │  │  partners        │  │  rate_limits     │  │
│  │  mcc_laws        │  │  queries_log     │  │  sessions        │  │
│  │  amendments      │  │  billing_events  │  │  cache           │  │
│  │                  │  │  feedback        │  │                  │  │
│  │  Each chunk has  │  │                 │  │                  │  │
│  │  metadata:       │  │                 │  │                  │  │
│  │  law_number      │  │                 │  │                  │  │
│  │  formats[]       │  │                 │  │                  │  │
│  │  authority       │  │                 │  │                  │  │
│  │  year            │  │                 │  │                  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Query Flow (End to End)

### 4.1 Simple Query Path (direct rule lookup)

```
User: "What is Law 36.1?"

1. Widget → POST /api/v1/chat { query: "What is Law 36.1?" }

2. API Middleware
   - Extract partner_id from X-API-Key header
   - Check Redis rate limit for partner
   - Log query to Postgres (async)

3. ChatService.query_understanding()
   - classify(): "simple_lookup" (no scenario keywords)
   - extract_entities(): { law_number: "36.1", format: null }

4. Route decision → Simple RAG Path

5. Retriever.hybrid_search(
     query="What is Law 36.1?",
     filters={ "law_number": "36.1" }
   )
   - Vector search for semantic match
   - BM25 keyword search for exact law number
   - Combine results with Reciprocal Rank Fusion

6. Re-ranker scores top-20 → returns top-5 chunks

7. Context Builder merges chunks into single context string

8. Gemini Pro call:
   System: "Answer using ONLY the provided context. Cite exact law numbers."
   Context: [retrieved law text for 36.1]
   User: "What is Law 36.1?"

9. Guardrails check response
   - Citation Grounding: "Law 36.1" exists in retrieved chunks? YES
   - Hallucination: Claims supported by context? YES
   - Format Check: Response doesn't contradict any format? PASS

10. Return ChatResponse with answer + citations
```

### 4.2 Scenario Path (complex multi-condition query)

```
User: "Ball pitched outside leg, hit in front of middle, 
       no bat involved, ball going on to hit top of off. What's the call?"

1. Same middleware steps as above

2. ChatService.query_understanding()
   - classify(): "scenario" (describes match situation)
   - extract_entities(): { 
       conditions: ["pitched outside leg", "impact in front", 
                    "no bat", "hitting off stump"],
       scenario_type: "lbw"
     }

3. Format detection → if unspecified, ask or default to common format

4. Route decision → Agent Path (ReAct loop)

5. Agent initialization
   - System prompt loaded
   - Tools registered: retrieve_law, check_condition, compare_formats,
     get_amendments, get_scenario_steps
   - Initial message: user scenario

6. ReAct Loop (continues until agent emits final answer or max turns):

   Turn 1:
   - LLM decides: call get_scenario_steps(scenario_type="lbw")
   - Tool returns ordered condition checklist for LBW
   - Appended to conversation

   Turn 2:
   - LLM decides: call check_condition(
       condition="Ball pitched outside leg stump",
       law_number="36.1",
       scenario="[user scenario]"
     )
   - Tool evaluates condition against scenario data
   - Returns: FAIL — "Ball pitched outside leg is automatic NOT OUT per Law 36.1"
   
   Turn 3:
   - LLM decides: condition is terminal (if false, stop)
   - Emits final answer with verdict + citation
   - Stops ReAct loop

7. Guardrails (same checks as simple path)

8. Return ChatResponse with verdict, step-by-step reasoning, citations
```

---

## 5. Ingestion Flow (Adding/Updating PDFs)

```
PDF file (ICC Playing Conditions 2025-26)
         │
         ▼
┌─────────────────────────────────────────┐
│  1. Parser (parser.py)                  │
│  - PyMuPDF extracts raw text            │
│  - Preserves page numbers, headings     │
│  - Detects table structures             │
│  - Output: list of {page, text, level}  │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  2. Chunker (chunker.py)                │
│  - Detects law number patterns:         │
│    "36.", "36.1", "36.1.1"             │
│  - Hierarchical split:                  │
│    Major law (36) → section             │
│    Sub-law (36.1) → primary chunk       │
│    Sub-sub (36.1.1) → sub-chunk         │
│  - Target chunk size: ~500 tokens       │
│  - Overlap: 50 tokens between chunks    │
│  - Output: list of LawChunk objects     │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  3. Metadata Tagger (metadata.py)       │
│  - Detect format: Test/ODI/T20I          │
│  - Detect authority: ICC or MCC          │
│  - Detect year / effective_date          │
│  - Extract law title from heading        │
│  - Attach metadata to each chunk         │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  4. Embed & Upsert                      │
│  - Generate embeddings via Gemini API    │
│  - Upsert to Qdrant with metadata        │
│  - Remove old chunks for same law+year   │
└─────────────────────────────────────────┘
                 │
                 ▼
         Ready for queries
```

---

## 6. Key Design Decisions

| Decision | Choice | Tradeoff Accepted |
|---|---|---|
| **Gemini Pro over GPT-4o** | $0.0015/1K input vs $0.01 | Slightly worse at complex tool chaining; guardrails compensate |
| **ReAct over LangChain** | Direct API control | More code to write; no framework lock-in |
| **Local re-ranker over API** | Free, no latency | Requires ~2GB memory for model |
| **Hybrid search over pure vector** | Higher retrieval accuracy | More complex retrieval pipeline |
| **Shadow DOM over iframe** | True CSS isolation, no CORS issues | Slightly more complex widget code |
| **SSE over WebSocket** | Simpler, auto-reconnect, HTTP/2 friendly | Unidirectional only (fine for chat) |

---

## 7. File Map

```
D:\AI\cricket-rule-bot\
├── app/
│   ├── main.py              ← FastAPI entry point. YOU build.
│   ├── config.py            ← Pydantic Settings. YOU build.
│   ├── models/
│   │   ├── types.py         ← Enums & type aliases. ME builds.
│   │   └── schemas.py       ← Pydantic models. ME builds.
│   ├── ingestion/
│   │   ├── parser.py        ← PDF text extraction. YOU build.
│   │   ├── chunker.py       ← Law-number chunking. YOU build.
│   │   └── metadata.py      ← Metadata extraction. YOU build.
│   ├── rag/
│   │   ├── embeddings.py    ← Gemini embedding client. YOU build.
│   │   ├── vector_store.py  ← Qdrant operations. YOU build.
│   │   ├── retriever.py     ← Hybrid search. ME builds.
│   │   └── re_ranker.py     ← Cross-encoder. ME builds.
│   ├── agent/
│   │   ├── tools.py         ← Tool definitions. ME builds.
│   │   ├── agent.py         ← ReAct loop. ME builds.
│   │   ├── scenarios.py     ← Condition graphs. ME builds.
│   │   └── format_router.py ← Format detection. ME builds.
│   ├── guardrails/
│   │   ├── citation.py      ← Citation verifier. ME builds.
│   │   ├── hallucination.py ← Factual check. ME builds.
│   │   ├── format_check.py  ← Format check. ME builds.
│   │   ├── confidence.py    ← Score gate. ME builds.
│   │   └── safety.py        ← Content filter. ME builds.
│   ├── api/
│   │   ├── routes.py        ← Endpoints. YOU build.
│   │   ├── middleware.py    ← Auth, rate limit. YOU build.
│   │   └── dependencies.py  ← DI. YOU build.
│   ├── services/
│   │   ├── chat_service.py  ← Orchestration. ME builds.
│   │   ├── partner_service.py ← Partner mgmt. YOU build.
│   │   └── usage_service.py ← Usage tracking. YOU build.
│   └── utils/
│       └── logger.py        ← Logging. ME builds.
├── frontend/
│   ├── widget/              ← Embeddable chat widget. YOU build.
│   └── admin/               ← Partner dashboard. YOU build.
├── tests/                   ← Test suite. BOTH build.
├── scripts/                 ← CLI utilities. YOU build.
└── docs/                    ← Documentation. ME builds.
```

---

## 8. Getting Started

### Prerequisites
- Python 3.11+
- Docker (for Qdrant, Redis, Postgres)
- Gemini API key from Google AI Studio

### Setup
```bash
git clone <repo>
cd cricket-rule-bot
cp .env.example .env
# Edit .env with your Gemini API key
docker-compose up -d qdrant redis postgres
pip install -r requirements.txt
python scripts/ingest_pdfs.py   # Ingests ICC/MCC PDFs
uvicorn app.main:app --reload
```

### Verify
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "X-API-Key: test-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Law 36.1?"}'
```
