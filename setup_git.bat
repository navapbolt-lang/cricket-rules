@echo off
echo ======================================
echo   CricketGPT - Git Setup
echo ======================================
echo.

cd /d D:\AI\cricket-rule-bot

echo [1/4] Initializing git...
git init

echo [2/4] Adding files...
git add .

echo [3/4] Creating initial commit...
git commit -m "Initial commit: CricketGPT - AI Cricket Rules Assistant

- RAG pipeline with hybrid search (vector + BM25 + RRF)
- Cross-encoder reranker
- Groq + Gemini LLM with fallback
- Web search augmentation (SerpAPI)
- Guardrails (citation + hallucination detection)
- Streaming responses (SSE)
- Decision Simulator UI
- Embeddable widget
- Docker support + Render deployment"

echo [4/4] Setting remote and pushing...
git remote add origin https://github.com/navapbolt-lang/cricket-rules.git
git branch -M main
git push -u origin main

echo.
echo ======================================
echo   Done! Check: https://github.com/navapbolt-lang/cricket-rules
echo ======================================
pause
