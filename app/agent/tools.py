"""Function definitions and implementations for Gemini Pro tool use."""

from typing import Optional
from app.models.types import Format, ToolResult
from app.rag.retriever import HybridRetriever
from app.rag.vector_store import VectorStore
from app.agent.scenarios import get_scenario_graph
from app.agent.format_router import format_to_string


# ── Tool declarations sent to Gemini Pro ──

RETRIEVE_LAW_DECLARATION = {
    "name": "retrieve_law",
    "description": "Retrieve the full text of a specific cricket law. Use when you need the exact wording or to verify a legal condition.",
    "parameters": {
        "type": "object",
        "properties": {
            "law_number": {
                "type": "string",
                "description": "Law number, e.g. '36.1', '36', '25.3'",
            },
            "format": {
                "type": "string",
                "enum": ["test", "odi", "t20i", "all"],
                "description": "Playing format (optional)",
            },
        },
        "required": ["law_number"],
    },
}

CHECK_CONDITION_DECLARATION = {
    "name": "check_condition",
    "description": "Check whether a specific legal condition is satisfied in a given match scenario. Returns pass/fail with legal reasoning.",
    "parameters": {
        "type": "object",
        "properties": {
            "condition": {
                "type": "string",
                "description": "The condition to check, e.g. 'ball pitched outside leg stump'",
            },
            "law_number": {
                "type": "string",
                "description": "The law number this condition falls under",
            },
            "scenario": {
                "type": "string",
                "description": "The full scenario from the user",
            },
        },
        "required": ["condition", "law_number", "scenario"],
    },
}

COMPARE_FORMATS_DECLARATION = {
    "name": "compare_formats",
    "description": "Compare how a law differs across Test, ODI, and T20I formats.",
    "parameters": {
        "type": "object",
        "properties": {
            "law_number": {
                "type": "string",
                "description": "Law number to compare across formats",
            }
        },
        "required": ["law_number"],
    },
}

GET_AMENDMENTS_DECLARATION = {
    "name": "get_amendments",
    "description": "Get recent amendments or changes to a specific law over time.",
    "parameters": {
        "type": "object",
        "properties": {
            "law_number": {
                "type": "string",
                "description": "Law number to check for amendments",
            }
        },
        "required": ["law_number"],
    },
}

GET_SCENARIO_STEPS_DECLARATION = {
    "name": "get_scenario_steps",
    "description": "Get the ordered checklist of conditions for a scenario type (LBW, run-out, DRS, etc.). Returns conditions the agent must verify step by step.",
    "parameters": {
        "type": "object",
        "properties": {
            "scenario_type": {
                "type": "string",
                "enum": [
                    "lbw", "run_out", "stumping", "hit_wicket",
                    "obstructing", "no_ball", "wide", "drs_review",
                    "boundary_catch", "concussion", "over_rate", "dls",
                    "timed_out",
                ],
                "description": "Type of cricket scenario",
            },
            "format": {
                "type": "string",
                "enum": ["test", "odi", "t20i", "all"],
                "description": "Playing format (optional)",
            },
        },
        "required": ["scenario_type"],
    },
}

TOOL_DECLARATIONS = [
    RETRIEVE_LAW_DECLARATION,
    CHECK_CONDITION_DECLARATION,
    COMPARE_FORMATS_DECLARATION,
    GET_AMENDMENTS_DECLARATION,
    GET_SCENARIO_STEPS_DECLARATION,
]


class CricketTools:
    """Implementations of cricket law tools for the ReAct agent."""

    def __init__(self, retriever: HybridRetriever, vector_store: VectorStore):
        self.retriever = retriever
        self.vs = vector_store

    def retrieve_law(self, law_number: str, format: Optional[str] = None) -> ToolResult:
        """Retrieve full law text for a given law number."""
        try:
            filters = {"law_number": law_number}
            if format and format != "all":
                filters["format"] = format

            chunks = self.retriever.search(
                query=f"Law {law_number}",
                filters=filters,
                top_k=3,
            )

            if not chunks:
                return ToolResult(
                    success=True,
                    data={"law_number": law_number, "text": f"Law {law_number} not found in the rulebook.", "formats": []},
                )

            return ToolResult(
                success=True,
                data={
                    "law_number": law_number,
                    "title": chunks[0].metadata.title,
                    "text": "\n\n".join(c.text for c in chunks),
                    "formats": [f.value for f in chunks[0].metadata.formats],
                    "authority": chunks[0].metadata.authority.value,
                    "year": chunks[0].metadata.year,
                },
            )
        except Exception as e:
            return ToolResult(success=False, data={}, error=str(e))

    def check_condition(self, condition: str, law_number: str, scenario: str) -> ToolResult:
        """Evaluate whether a specific condition is met in a scenario using condition graphs."""
        try:
            law_text_result = self.retrieve_law(law_number)
            law_text = law_text_result.data.get("text", "")

            scenario_lower = scenario.lower()
            condition_lower = condition.lower()

            passed = True
            reasoning_parts = []

            if "outside leg" in condition_lower or "pitched outside leg" in condition_lower:
                if "outside leg" in scenario_lower:
                    passed = False
                    reasoning_parts.append(
                        "Ball pitched outside leg stump. Per Law 36.1, "
                        "this is automatic NOT OUT regardless of other conditions."
                    )
                else:
                    reasoning_parts.append("Ball pitched in line or on off side. Condition satisfied.")

            if "impact in line" in condition_lower:
                if "in front" in scenario_lower or "hit in front" in scenario_lower:
                    reasoning_parts.append("Impact in line with stumps. Condition satisfied.")
                else:
                    passed = False
                    reasoning_parts.append("Impact not in line with stumps.")

            if "ball would have hit" in condition_lower or "trajectory" in condition_lower:
                hitting_terms = ["hit", "going on to", "would have hit", "hitting"]
                if any(t in scenario_lower for t in hitting_terms):
                    reasoning_parts.append("Ball projected to hit the stumps. Condition satisfied.")
                else:
                    passed = False
                    reasoning_parts.append("Ball projected to miss the stumps.")

            if "bat" in condition_lower and "hit" in condition_lower:
                if "bat" in scenario_lower and ("hit" in scenario_lower or "edge" in scenario_lower):
                    if "no bat" not in scenario_lower and "bat not involved" not in scenario_lower and "bat involved" in scenario_lower:
                        reasoning_parts.append("Bat was involved before the ball hit the pad.")
                    else:
                        reasoning_parts.append("Bat not involved before impact. Condition satisfied.")

            is_terminal = "outside leg" in condition_lower or "would have hit" in condition_lower

            return ToolResult(
                success=True,
                data={
                    "condition": condition,
                    "condition_met": passed,
                    "reasoning": " ".join(reasoning_parts) if reasoning_parts else f"Checked condition: {condition}",
                    "law_reference": f"Law {law_number}",
                    "terminal": is_terminal,
                    "law_text": law_text[:500] if law_text else "",
                },
            )
        except Exception as e:
            return ToolResult(success=False, data={}, error=str(e))

    def compare_formats(self, law_number: str) -> ToolResult:
        """Compare a law across formats by retrieving format-specific versions."""
        try:
            results = {}
            for fmt in ["test", "odi", "t20i"]:
                res = self.retrieve_law(law_number, fmt)
                results[fmt] = res.data.get("text", "")[:300] if res.success else "Not found"

            return ToolResult(
                success=True,
                data={
                    "law_number": law_number,
                    "test": results.get("test", ""),
                    "odi": results.get("odi", ""),
                    "t20i": results.get("t20i", ""),
                    "note": "Differences across formats are shown above. If identical, the law applies uniformly."
                },
            )
        except Exception as e:
            return ToolResult(success=False, data={}, error=str(e))

    def get_amendments(self, law_number: str) -> ToolResult:
        """Get amendments for a law from the vector store."""
        try:
            filters = {"parent_law": law_number.split(".")[0]}
            chunks = self.retriever.search(
                query=f"amendment change update Law {law_number}",
                filters=filters,
                top_k=5,
            )

            amendments = []
            for c in chunks:
                if "amendment" in c.text.lower() or "change" in c.text.lower() or "updated" in c.text.lower():
                    amendments.append({
                        "year": c.metadata.year,
                        "text": c.text[:200],
                    })

            if not amendments:
                return ToolResult(
                    success=True,
                    data={
                        "law_number": law_number,
                        "amendments": [],
                        "note": "No recent amendments found for this law.",
                    },
                )

            return ToolResult(
                success=True,
                data={"law_number": law_number, "amendments": amendments},
            )
        except Exception as e:
            return ToolResult(success=False, data={}, error=str(e))

    def get_scenario_steps(self, scenario_type: str, format: Optional[str] = None) -> ToolResult:
        """Get condition checklist for a scenario type."""
        try:
            conditions = get_scenario_graph(scenario_type, format or "all")

            return ToolResult(
                success=True,
                data={
                    "scenario_type": scenario_type,
                    "format": format or "all",
                    "conditions": [
                        {
                            "id": c.id,
                            "description": c.description,
                            "law": c.law,
                            "terminal": c.terminal,
                        }
                        for c in conditions
                    ],
                },
            )
        except Exception as e:
            return ToolResult(success=False, data={}, error=str(e))
