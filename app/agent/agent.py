from typing import Optional
import json
from app.config import settings
from app.agent.tools import CricketTools, TOOL_DECLARATIONS
from app.models.schemas import ChatResponse, Citation
from app.models.types import Format, Authority


SYSTEM_PROMPT = """You are a cricket rules expert assistant. Answer questions about cricket laws with exact citations.

CORE RULES:
1. ALWAYS cite the exact law number for every claim you make.
2. If a law varies by format (Test/ODI/T20I), specify which format applies.
3. If you are unsure, say "I am not confident" — do not guess.
4. Use the tools provided to retrieve and verify law text.

SCENARIO HANDLING:
When a user describes a match scenario:
1. Use get_scenario_steps to get the condition checklist.
2. Check each condition using check_condition or retrieve_law.
3. Explain which conditions pass/fail and why.
4. Give a clear verdict with all applicable law citations.

RESPONSE FORMAT:
- Start with the verdict: "OUT" or "NOT OUT" or the appropriate decision.
- Step through each condition with its result.
- End with law citations."""


class Agent:
    def __init__(self, tools: CricketTools):
        self.tools = tools
        self._client = None

    def _get_client(self):
        if self._client is None:
            if settings.llm_provider == "groq":
                from groq import Groq
                self._client = Groq(api_key=settings.groq_api_key)
            else:
                import google.generativeai as genai
                genai.configure(api_key=settings.gemini_api_key)
                self._client = genai
        return self._client

    async def run(self, query: str, format: Optional[str] = None) -> ChatResponse:
        max_turns = 10
        turn_count = 0
        citations_collected = []
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        client = self._get_client()

        while turn_count < max_turns:
            turn_count += 1
            if len(messages) > 6:
                messages = [messages[0], messages[1]] + messages[-4:]

            if settings.llm_provider == "groq":
                groq_tools = [{"type": "function", "function": td} for td in TOOL_DECLARATIONS]
                try:
                    resp = client.chat.completions.create(
                        model=settings.llm_model,
                        messages=messages,
                        tools=groq_tools,
                        tool_choice="auto",
                        temperature=0.1,
                        max_tokens=2048,
                    )
                except Exception as e:
                    err = str(e)
                    if "rate_limit" in err.lower() or "429" in err:
                        return ChatResponse(
                            answer="The AI service is temporarily rate-limited. Please try again in a few minutes.",
                            citations=[], confidence=0.3,
                            suggested_questions=["What is Law 36?", "How does DRS work?"],
                            guardrail_status="rate_limited",
                        )
                    if "context_length" in err.lower() or "too many tokens" in err.lower():
                        return ChatResponse(
                            answer="The question is too complex. Try breaking it into simpler parts.",
                            citations=[], confidence=0.3,
                            suggested_questions=["What is Law 36?", "How does DRS work?"],
                            guardrail_status="context_exceeded",
                        )
                    raise
                msg = resp.choices[0].message

                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_name = tc.function.name
                        tool_args = json.loads(tc.function.arguments)
                        result = self._execute_tool(tool_name, tool_args)
                        messages.append(msg)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result.data if hasattr(result, "data") else result),
                        })
                else:
                    text = msg.content or ""
                    if text:
                        return self._parse_response(text, citations_collected, query)
            else:
                import google.generativeai as genai
                model = genai.GenerativeModel(
                    model_name=settings.llm_model,
                    system_instruction=SYSTEM_PROMPT,
                    tools=TOOL_DECLARATIONS,
                    generation_config=genai.types.GenerationConfig(temperature=0.1),
                )
                response = model.generate_content(query)
                if response.candidates:
                    part = response.candidates[0].content.parts[0]
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        tool_name = fc.name
                        tool_args = dict(fc.args)
                        result = self._execute_tool(tool_name, tool_args)
                        messages.append({
                            "role": "model",
                            "parts": [genai.protos.FunctionResponse(
                                name=tool_name,
                                response={"result": result.data if hasattr(result, "data") else result},
                            )],
                        })
                    else:
                        text = part.text if hasattr(part, "text") else ""
                        if text:
                            return self._parse_response(text, citations_collected, query)

        return ChatResponse(
            answer="I couldn't determine the answer with the available information. Please rephrase your scenario.",
            citations=[],
            confidence=0.3,
            suggested_questions=["What is Law 36.1?", "How does DRS work?"],
            format_used=Format(format) if format else None,
            guardrail_status="max_turns_exceeded",
        )

    def _execute_tool(self, tool_name: str, args: dict) -> object:
        tool_map = {
            "retrieve_law": self.tools.retrieve_law,
            "check_condition": self.tools.check_condition,
            "compare_formats": self.tools.compare_formats,
            "get_amendments": self.tools.get_amendments,
            "get_scenario_steps": self.tools.get_scenario_steps,
        }
        handler = tool_map.get(tool_name)
        if not handler:
            return type("obj", (object,), {
                "success": False,
                "data": {"error": f"Unknown tool: {tool_name}"},
            })()
        return handler(**args)

    def _parse_response(self, text: str, citations_used: list, query: str) -> ChatResponse:
        import re
        law_refs = re.findall(r"Law\s+(\d+(?:\.\d+)*)", text)
        unique_laws = list(set(law_refs))
        citations = [
            Citation(law_number=law, text="", formats=[Format.ALL], authority=Authority.ICC, year=2025)
            for law in unique_laws
        ]
        from app.agent.format_router import detect_format
        fmt = detect_format(query)
        confidence = 0.85
        if "not confident" in text.lower() or "uncertain" in text.lower():
            confidence = 0.3
        return ChatResponse(
            answer=text,
            citations=citations,
            confidence=confidence,
            suggested_questions=[
                "What is umpire's call?",
                "How many DRS reviews in a Test match?",
                "What is a no-ball?",
            ],
            format_used=fmt,
            guardrail_status="passed",
        )
