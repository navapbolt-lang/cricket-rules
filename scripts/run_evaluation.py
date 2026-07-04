"""Run batch evaluation against test scenarios.

Usage: python scripts/run_evaluation.py

Loads scenarios from data/evaluation/scenarios.json,
runs each through the pipeline, computes metrics,
and saves results to data/evaluation/results/.
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.schemas import ChatRequest
from app.rag.retriever import HybridRetriever
from app.rag.re_ranker import ReRanker
from app.rag.vector_store import VectorStore
from app.rag.embeddings import EmbeddingClient
from app.agent.tools import CricketTools
from app.agent.agent import Agent
from app.services.chat_service import ChatService

EVALUATION_FILE = Path("data/evaluation/scenarios.json")
RESULTS_DIR = Path("data/evaluation/results")


def _load_scenarios():
    with open(EVALUATION_FILE) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "scenarios" in data:
        return data["scenarios"]
    return []


def _init_service() -> ChatService:
    emb = EmbeddingClient()
    vs = VectorStore()
    ret = HybridRetriever(vs, emb)
    rerank = ReRanker()
    tools = CricketTools(ret, vs)
    agent = Agent(tools)
    return ChatService(ret, rerank, agent)


def _verdict_accurate(response_text: str, expected: str) -> bool:
    resp_upper = response_text.upper()
    exp_upper = expected.upper()
    return exp_upper in resp_upper


def run_evaluation():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    scenarios = _load_scenarios()
    if not scenarios:
        print(f"No scenarios found in {EVALUATION_FILE}")
        return

    print(f"Running evaluation on {len(scenarios)} scenarios...")
    service = _init_service()

    results = []
    correct = 0

    for i, scenario in enumerate(scenarios, 1):
        query = scenario.get("query", "")
        expected = scenario.get("expected", "N/A")
        law = scenario.get("law", "")

        print(f"  [{i}/{len(scenarios)}] {query[:60]}...", end=" ", flush=True)

        start = time.time()
        try:
            req = ChatRequest(query=query)
            resp = service.process(req)
            latency = (time.time() - start) * 1000
            answer = resp.answer if hasattr(resp, "answer") else str(resp)
            accurate = _verdict_accurate(answer, expected) if expected != "N/A" else None
            if accurate:
                correct += 1
            results.append({
                "query": query,
                "expected": expected,
                "law": law,
                "response": answer[:500],
                "guardrail_status": getattr(resp, "guardrail_status", "unknown"),
                "confidence": getattr(resp, "confidence", 0),
                "latency_ms": round(latency, 1),
                "verdict_accurate": accurate,
            })
            status = "✓" if accurate else "✗"
            print(f"{status} ({latency:.0f}ms)")
        except Exception as e:
            results.append({
                "query": query,
                "expected": expected,
                "law": law,
                "response": f"ERROR: {e}",
                "guardrail_status": "error",
                "confidence": 0,
                "latency_ms": 0,
                "verdict_accurate": False,
            })
            print(f"ERROR: {e}")

    total = len(scenarios)
    accuracy = (correct / total * 100) if total > 0 else 0
    avg_latency = sum(r["latency_ms"] for r in results) / total if total > 0 else 0

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": total,
        "verdict_accuracy_pct": round(accuracy, 1),
        "correct_verdicts": correct,
        "avg_latency_ms": round(avg_latency, 1),
        "guardrail_breakdown": {},
    }
    for r in results:
        gs = r["guardrail_status"]
        summary["guardrail_breakdown"][gs] = summary["guardrail_breakdown"].get(gs, 0) + 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    result_file = RESULTS_DIR / f"eval_{timestamp}.json"
    with open(result_file, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    print(f"\n{'='*50}")
    print(f"  Results saved to: {result_file}")
    print(f"  Verdict Accuracy: {accuracy:.1f}% ({correct}/{total})")
    print(f"  Avg Latency:      {avg_latency:.0f}ms")
    print(f"{'='*50}")


if __name__ == "__main__":
    run_evaluation()
