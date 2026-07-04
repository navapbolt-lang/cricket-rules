# Cricket Rules AI 🏏

A B2B embeddable AI chatbot that answers cricket rule questions with **exact law citations**. Partners embed a single `<script>` tag and get a branded, context-aware rules assistant on their site.

## Architecture

```
Partner Site (Hotstar/Cricbuzz)  
        │
        ├── <script> embed.js ──→ Shadow DOM Widget
        │                              │
        ▼                              ▼
   FastAPI Backend ←── POST /chat ────┘
        │
        ├── RAG Pipeline (Hybrid Search + Cross-encoder)
        ├── Agent Engine (ReAct + Gemini Pro function calling)
        └── Guardrails (Citation, Hallucination, Format, Safety)
```

## Tech Stack

| Component | Choice |
|---|---|
| LLM | Gemini Pro |
| Backend | Python 3.11+ / FastAPI |
| Vector DB | Qdrant (hybrid search) |
| Embeddings | Gemini Embedding API |
| Re-ranker | BGE-reranker-v2-m3 |
| Widget | Vanilla JS + Shadow DOM |
| Infra | Docker / Railway / Render |

## Quick Start

```bash
# 1. Clone and enter directory
cd cricket-rule-bot

# 2. Copy env file and add your Gemini API key
cp .env.example .env

# 3. Start infrastructure
docker-compose up -d qdrant redis postgres

# 4. Install dependencies
pip install -r requirements.txt

# 5. Place ICC/MCC PDFs in data/pdfs/ and ingest
python scripts/ingest_pdfs.py

# 6. Start the server
uvicorn app.main:app --reload

# 7. Test it
curl -X POST http://localhost:8000/api/v1/chat \
  -H "X-API-Key: test-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Law 36.1?"}'
```

## Project Structure

```
cricket-rule-bot/
├── app/                    # Python backend
│   ├── ingestion/         # PDF parsing & chunking (YOU)
│   ├── rag/               # Retrieval pipeline (ME: retriever, re-ranker)
│   ├── agent/             # ReAct agent + tools (ME: agent, tools, scenarios)
│   ├── guardrails/        # Safety & accuracy checks (ME: citation, hallucination)
│   ├── api/               # FastAPI endpoints (YOU)
│   ├── services/          # Business logic (ME: chat_service; YOU: partner, usage)
│   └── models/            # Pydantic schemas & types (ME)
├── frontend/
│   ├── widget/            # Embeddable JS widget (YOU)
│   └── admin/             # Partner dashboard (YOU)
├── docs/                  # Architecture & design docs (ME)
├── tests/                 # Test suite (BOTH)
├── scripts/               # CLI utilities (YOU)
└── data/                  # PDFs, chunks, evaluation scenarios
```

## API

See `docs/API_REFERENCE.md` for full API documentation.

## Business Model

| Product | Price | Target |
|---|---|---|
| Embeddable Widget (Starter) | ₹25K/yr | Small cricket sites, academies |
| Embeddable Widget (Pro) | ₹1L/yr | Mid-size cricket platforms |
| Enterprise | Custom | Hotstar, Cricbuzz, Dream11 |
| Academy Training Platform | ₹2-5L/yr | Umpire certification, coaching |

## License

Proprietary — see LICENSE file.
