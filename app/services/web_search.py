"""Web search service using SerpAPI for real-time cricket stats and records."""

import re
from typing import Optional
from app.config import settings
from app.agent.llm_client import generate_text
from app.utils.key_manager import key_manager


class WebSearchService:
    """Service to fetch real-time cricket knowledge from Google via SerpAPI."""

    def __init__(self):
        self.enabled = True

    def should_search(self, query: str) -> bool:
        """Determine if a query would benefit from web search.

        Only triggers for questions where stats/records add value:
        - Famous incidents, controversial decisions
        - Record-breaking performances
        - Historical milestones

        Does NOT trigger for:
        - Simple law lookups ("What is Law 36?")
        - Basic definitions ("What is a wide ball?")
        - Rare rules with few records ("timed out")
        """
        query_lower = query.lower()

        # Skip simple law lookups
        skip_patterns = [
            r"^(what is|explain|define|tell me about)\s+(law|rule)\s+\d+",
            r"^(what is|explain|define)\s+(a|the)?\s*(wide|no.?ball|lbw|bye|leg.?bye)$",
            r"^law\s+\d+",
        ]
        for pattern in skip_patterns:
            if re.search(pattern, query_lower):
                return False

        # Interesting topics where stats add value
        interesting_patterns = [
            # Famous incidents
            r"lbw",
            r"leg before",
            r"drs",
            r"review",
            r"umpire's?\s+call",
            r"controvers",
            r"dismiss",
            # Records & milestones
            r"first (player|batsman|bowler)",
            r"last (player|batsman|bowler)",
            r"fastest (century|five|wicket|run)",
            r"highest (score|total|partnership)",
            r"lowest (score|total)",
            r"most (runs|wickets|centuries|sixes|fours)",
            r"record",
            r"hat.?trick",
            r"double century",
            r"century",
            r"five.?wicket",
            r"ten.?wicket",
            # Historical
            r"when (was|did|has)",
            r"who (was|is|were|has)",
            r"history",
            r"never happened",
            r"only time",
            r"first time",
            r"world cup",
            r"final",
        ]

        for pattern in interesting_patterns:
            if re.search(pattern, query_lower):
                return True

        return False

    def search(self, query: str) -> str:
        """Perform web search via SerpAPI and return formatted results."""
        api_key = key_manager.get_key("serpapi")
        if not api_key:
            return self._fallback_search(query)

        try:
            from serpapi import GoogleSearch

            # Optimize search query for cricket
            cricket_query = f"{query} cricket records statistics"

            params = {
                "q": cricket_query,
                "api_key": api_key,
                "num": 3,
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            # Check for rate limit
            if "error" in results and "rate" in results.get("error", "").lower():
                key_manager.mark_rate_limited("serpapi", api_key, cooldown_seconds=60)
                return self._fallback_search(query)

            # Extract organic results
            organic = results.get("organic_results", [])
            if not organic:
                return self._fallback_search(query)

            # Format the top results
            facts = []
            for i, result in enumerate(organic[:3], 1):
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                if snippet:
                    facts.append(f"{i}. {title}: {snippet}")

            return "\n".join(facts)

        except Exception as e:
            return self._fallback_search(query)

    def _fallback_search(self, query: str) -> str:
        """Fallback to LLM-based knowledge when SerpAPI is unavailable."""
        try:
            prompt = f"""Provide 2-3 key cricket facts about: {query}

Focus on:
- Specific player names, dates, venues
- Record holders and milestones
- Historical firsts and lasts

Keep it brief and factual. One fact per line."""

            result = generate_text(prompt, temperature=0.3, max_tokens=300)
            return result
        except Exception:
            return "Web search unavailable."

    def format_for_context(self, query: str, web_results: str) -> str:
        """Format web search results for inclusion in LLM context."""
        if not web_results or "unavailable" in web_results.lower():
            return ""

        return f"\n\nCRICKET STATS & RECORDS (from web):\n{web_results}"
