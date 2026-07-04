"""Main chat orchestration service — routes queries through the full pipeline."""

from typing import Optional
import re
from app.config import settings
from app.models.schemas import ChatRequest, ChatResponse, Citation
from app.models.types import (
    QueryType,
    Format,
    Authority,
    GuardrailResult,
    GuardrailName,
    LawChunk,
    ChunkMetadata,
    ChunkType,
)
from app.rag.retriever import HybridRetriever
from app.rag.re_ranker import ReRanker
from app.agent.agent import Agent
from app.agent.format_router import detect_format, format_to_string
from app.agent.llm_client import generate_text
from app.guardrails.citation import verify_citations
from app.guardrails.hallucination import check_factual_consistency
from app.guardrails.format_check import check_format_consistency
from app.guardrails.confidence import should_serve_response, get_safe_refusal_response
from app.services.web_search import WebSearchService


SIMPLE_QUERY_TEMPLATE = """Answer the following cricket rules question using the provided context.

CONTEXT:
{context}

QUESTION: {query}

INSTRUCTIONS:
- Start with the verdict/answer first, then explain.
- Always cite the exact law number (e.g. "Law 36.1.1") for every claim about rules.
- If the context includes "CRICKET STATS & RECORDS", weave those facts naturally into your answer.
- Use this exact format for your answer:

**Verdict:** [clear answer]
**Law:** Law X.Y.Z (if applicable)
**Explanation:** [2-3 sentences explaining the rule]
**Notable:** [if stats/records are available, add a line like "First player to...: [Name]" or "Record holder: [Name] - [stat]"]
**Format variation:** [if the rule differs by format, list it. If not, omit this line]

- If the context doesn't contain the answer, say: "I don't have enough information to answer this question."
- If a law varies by format (Test/ODI/T20I), always mention the differences.
- Be concise. No more than 6 sentences total.
- Combine the law explanation with the stats naturally — don't make them feel like separate sections."""


class ChatService:
    """Orchestrates the end-to-end chat pipeline.

    Flow:
    1. classify_query — determine simple RAG or agent route
    2. detect_format — identify playing format
    3. If simple → RAG only (retrieve → rerank → generate)
    4. If scenario → Agent (ReAct loop with tools)
    5. Run guardrails on the generated response
    6. Return ChatResponse or safe refusal
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        re_ranker: ReRanker,
        agent: Agent,
        usage_service=None,
        partner_service=None,
    ):
        self.retriever = retriever
        self.re_ranker = re_ranker
        self.agent = agent
        self.usage_service = usage_service
        self.partner_service = partner_service
        self.web_search = WebSearchService()

    TOPIC_LAWS = {
        "timed out": "40",
        "time out": "40",
        "timeout": "40",
        "lbw": "36",
        "leg before wicket": "36",
        "run out": "38",
        "run-out": "38",
        "stumping": "39",
        "stump": "39",
        "no ball": "21",
        "no-ball": "21",
        "wide": "22",
        "wide ball": "22",
        "hit wicket": "35",
        "hit-wicket": "35",
        "obstructing": "37",
        "obstruction": "37",
        "drs": "36",
        "review": "36",
        "bye": "23",
        "leg bye": "23",
        "catch": "33",
        "caught": "33",
        "bowled": "30",
        "dead ball": "20",
        "free hit": "21",
    }

    async def process(
        self,
        request: ChatRequest,
        partner_id: str = "",
        db_sessionmaker=None,
        redis=None,
    ) -> ChatResponse:
        """Process a chat request end-to-end with usage tracking."""
        import time

        start = time.time()

        query = request.query.strip().lower()
        preferred_format = request.format

        query_type = self.classify_query(query)
        detected_format = detect_format(query, preferred_format)
        fmt_str = detected_format.value if detected_format else "unknown"

        if query_type == QueryType.SCENARIO:
            response = await self.agent.run(
                query, fmt_str if fmt_str != "unknown" else None
            )
            latency = (time.time() - start) * 1000
            await self._track(
                partner_id, query, response, fmt_str, latency, db_sessionmaker, redis
            )
            return response

        chunks = self.retriever.search(
            query=query,
            filters={},
            top_k=5,
        )
        chunks = self.re_ranker.rerank(query, chunks, top_k=2)

        max_score = max((c.score or 0.0) for c in chunks) if chunks else 0.0
        if max_score < 0.3 and chunks:
            for topic, law_num in self.TOPIC_LAWS.items():
                if topic in query:
                    law_chunks = self.retriever.search(
                        query=f"Law {law_num}",
                        filters={},
                        top_k=3,
                    )
                    if law_chunks:
                        chunks = self.re_ranker.rerank(
                            f"Law {law_num}", law_chunks, top_k=2
                        )
                        break

        if not chunks:
            response = ChatResponse(
                answer="I couldn't find relevant law information for your question. Try specifying a law number (e.g., 'Law 36.1') or a specific format (Test/ODI/T20I).",
                citations=[],
                confidence=0.1,
                suggested_questions=["What is Law 36.1?", "How does DRS work?"],
                format_used=detected_format,
                guardrail_status="no_context",
            )
            latency = (time.time() - start) * 1000
            await self._track(
                partner_id, query, response, fmt_str, latency, db_sessionmaker, redis
            )
            return response

        context = self.build_context(chunks)

        # Check if web search would supplement the answer
        web_context = ""
        use_web_search = (
            request.web_search
            if request.web_search is not None
            else settings.web_search_enabled
        )
        if use_web_search and self.web_search.should_search(query):
            web_results = self.web_search.search(query)
            web_context = self.web_search.format_for_context(query, web_results)

        # Combine vector store context with web search context
        full_context = context + web_context

        answer = self._generate_simple_answer(query, full_context)

        max_score = max((c.score or 0.0) for c in chunks)
        guardrail_results = self.run_guardrails(answer, chunks, detected_format)
        should_serve = should_serve_response(max_score, guardrail_results)

        if not should_serve:
            fallback = await self.agent.run(
                query, fmt_str if fmt_str != "unknown" else None
            )
            if fallback.answer and "not confident" not in fallback.answer.lower():
                response = fallback
            else:
                refusal = get_safe_refusal_response()
                response = ChatResponse(**refusal)
            latency = (time.time() - start) * 1000
            await self._track(
                partner_id, query, response, fmt_str, latency, db_sessionmaker, redis
            )
            return response

        law_refs = re.findall(r"Law\s+(\d+(?:\.\d+)*)", answer)
        cited_laws = set(law_refs)
        citations = []
        for c in chunks:
            if c.metadata.law_number in cited_laws or any(
                c.metadata.law_number.startswith(l)
                or l.startswith(c.metadata.law_number)
                for l in cited_laws
            ):
                citations.append(
                    Citation(
                        law_number=c.metadata.law_number,
                        text=c.text[:200],
                        formats=[f for f in c.metadata.formats],
                        authority=c.metadata.authority,
                        year=c.metadata.year,
                    )
                )

        all_passed = all(r.passed for r in guardrail_results)
        status = "passed" if all_passed else "guardrail_warning"

        response = ChatResponse(
            answer=answer,
            citations=citations,
            confidence=min(max_score + 0.1, 1.0),
            suggested_questions=[
                "What is umpire's call?",
                "How many DRS reviews per innings?",
                "What is a no-ball?",
            ],
            format_used=detected_format,
            guardrail_status=status,
        )

        latency = (time.time() - start) * 1000
        await self._track(
            partner_id, query, response, fmt_str, latency, db_sessionmaker, redis
        )
        return response

    async def _track(
        self,
        partner_id: str,
        query: str,
        response: ChatResponse,
        fmt: str,
        latency_ms: float,
        db_sessionmaker,
        redis,
    ):
        """Log query event and record usage."""
        from app.utils.logger import log_query_event, log_guardrail_failure

        log_query_event(partner_id, query, fmt, latency_ms, response.guardrail_status)

        if response.guardrail_status != "passed":
            log_guardrail_failure("pipeline", response.guardrail_status, partner_id)

        if self.usage_service:
            await self.usage_service.increment_usage(partner_id, redis=redis)
            await self.usage_service.log_query(
                partner_id=partner_id,
                query=query,
                response=response.answer,
                format_used=fmt,
                latency_ms=latency_ms,
                guardrail_status=response.guardrail_status,
                confidence=response.confidence,
                db_sessionmaker=db_sessionmaker,
            )

    def classify_query(self, query: str) -> QueryType:
        """Classify the query type based on content heuristics."""
        q = query.lower()

        scenario_patterns = [
            r"what (if|happens|will happen)",
            r"(ball|delivery) (pitched|bowled|landed)",
            r"(hit|struck|impact) (in front|outside|on)",
            r"going on to",
            r"no bat",
            r"would have (hit|gone)",
            r"what('s| is) the (decision|call|ruling)",
            r"is (that|this) (out|not out|a (no.?ball|wide))",
            r"(player|batter|fielder) (comes|arrive|replace|substitut)",
            r"what (rule|law) applies",
            r"can (a|the) (batter|fielder|player)",
        ]
        for pattern in scenario_patterns:
            if re.search(pattern, q):
                return QueryType.SCENARIO

        comparison_patterns = [
            r"difference between",
            r"compare",
            r"vs\.?",
            r"versus",
        ]
        for pattern in comparison_patterns:
            if re.search(pattern, q):
                return QueryType.COMPARISON

        definition_patterns = [
            r"^what (is|are|does)",
            r"^define",
            r"^explain",
        ]
        for pattern in definition_patterns:
            if re.search(pattern, q):
                return QueryType.DEFINITION

        law_pattern = r"(law\s+\d+|section\s+\d+|rule\s+\d+)"
        if re.search(law_pattern, q):
            return QueryType.SIMPLE_LOOKUP

        return QueryType.SIMPLE_LOOKUP

    def build_context(self, chunks: list[LawChunk]) -> str:
        """Build a context string from retrieved chunks for the LLM."""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(
                f"[{i}] Law {chunk.metadata.law_number} ({chunk.metadata.title})\n"
                f"Format: {', '.join(f.value for f in chunk.metadata.formats)}\n"
                f"{chunk.text[:500]}"
            )
        return "\n\n---\n\n".join(parts)

    def _generate_simple_answer(self, query: str, context: str) -> str:
        try:
            prompt = SIMPLE_QUERY_TEMPLATE.format(context=context, query=query)
            answer = generate_text(prompt, temperature=0.1, max_tokens=1024)
            answer = self._strip_markdown(answer)
            return answer
        except Exception:
            return "I encountered an error generating the answer. Please try rephrasing your question."

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove markdown bold/italic markers from LLM output."""
        import re

        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"_(.+?)_", r"\1", text)
        return text

    def run_guardrails(
        self,
        response: str,
        chunks: list[LawChunk],
        detected_format: Optional[Format],
    ) -> list[GuardrailResult]:
        """Run all guardrails on the response. Returns list of results."""
        results = []

        try:
            cit_result = verify_citations(response, chunks)
            results.append(
                GuardrailResult(
                    name=GuardrailName.CITATION,
                    passed=cit_result.all_valid,
                    details={
                        "invalid": cit_result.invalid_citations,
                        "unsupported": len(cit_result.unsupported_claims),
                    },
                )
            )
        except Exception as e:
            results.append(
                GuardrailResult(
                    name=GuardrailName.CITATION, passed=False, details={"error": str(e)}
                )
            )

        try:
            context = self.build_context(chunks)
            hal_result = check_factual_consistency(response, context)
            results.append(
                GuardrailResult(
                    name=GuardrailName.HALLUCINATION,
                    passed=hal_result.is_consistent,
                    details={
                        "failed_count": len(hal_result.failed_claims),
                        "failures": hal_result.failed_claims[:3],
                    },
                )
            )
        except Exception as e:
            results.append(
                GuardrailResult(
                    name=GuardrailName.HALLUCINATION,
                    passed=False,
                    details={"error": str(e)},
                )
            )

        try:
            fmt_result = check_format_consistency(response, detected_format, chunks)
            results.append(
                GuardrailResult(
                    name=GuardrailName.FORMAT_CHECK,
                    passed=fmt_result.is_consistent,
                    details={
                        "mismatches": fmt_result.mismatches,
                        "note": fmt_result.note,
                    },
                )
            )
        except Exception as e:
            results.append(
                GuardrailResult(
                    name=GuardrailName.FORMAT_CHECK,
                    passed=True,
                    details={"error": str(e)},
                )
            )

        return results
