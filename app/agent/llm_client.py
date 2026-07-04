import json
import logging
from typing import Optional
from app.config import settings
from app.utils.key_manager import key_manager

logger = logging.getLogger(__name__)


def _call_groq(prompt: str, temperature: float, max_tokens: int) -> str:
    from groq import Groq

    api_key = key_manager.get_key("groq")
    if not api_key:
        raise ValueError("No Groq API keys available")

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        err = str(e).lower()
        if "rate_limit" in err or "429" in err or "tokens per day" in err:
            key_manager.mark_rate_limited("groq", api_key, cooldown_seconds=120)
            raise
        raise


def _call_gemini(prompt: str, temperature: float, max_tokens: int) -> str:
    import google.generativeai as genai

    api_key = key_manager.get_key("gemini")
    if not api_key:
        raise ValueError("No Gemini API keys available")

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        err = str(e).lower()
        if "rate_limit" in err or "429" in err or "quota" in err:
            key_manager.mark_rate_limited("gemini", api_key, cooldown_seconds=120)
            raise
        raise


def generate_text(prompt: str, temperature: float = 0.1, max_tokens: int = 1024) -> str:
    if settings.llm_provider == "groq":
        try:
            return _call_groq(prompt, temperature, max_tokens)
        except Exception as e:
            err = str(e).lower()
            if "rate_limit" in err or "429" in err or "tokens per day" in err:
                logger.warning("Groq rate limited, falling back to Gemini")
                try:
                    return _call_gemini(prompt, temperature, max_tokens)
                except Exception as e2:
                    logger.error(f"Gemini fallback also failed: {e2}")
                    return "The AI service is temporarily rate-limited. Please try again in a few minutes."
            raise
    return _call_gemini(prompt, temperature, max_tokens)


def _groq_with_tools(
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> tuple[str, Optional[dict]]:
    from groq import Groq

    api_key = key_manager.get_key("groq")
    if not api_key:
        raise ValueError("No Groq API keys available")

    try:
        client = Groq(api_key=api_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            tc = msg.tool_calls[0]
            args = json.loads(tc.function.arguments)
            return "", {"name": tc.function.name, "arguments": args}
        return msg.content.strip() or "", None
    except Exception as e:
        err = str(e).lower()
        if "rate_limit" in err or "429" in err or "tokens per day" in err:
            key_manager.mark_rate_limited("groq", api_key, cooldown_seconds=120)
        raise


def _gemini_with_tools(
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> tuple[str, Optional[dict]]:
    import google.generativeai as genai

    api_key = key_manager.get_key("gemini")
    if not api_key:
        raise ValueError("No Gemini API keys available")

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(settings.llm_model)
        resp = model.generate_content(
            [system_prompt, user_message],
            tools=tools,
            generation_config=genai.types.GenerationConfig(temperature=temperature),
        )
        if resp.candidates and resp.candidates[0].content.parts[0].function_call:
            fc = resp.candidates[0].content.parts[0].function_call
            return "", {"name": fc.name, "arguments": dict(fc.args)}
        return resp.text.strip(), None
    except Exception as e:
        err = str(e).lower()
        if "rate_limit" in err or "429" in err or "quota" in err:
            key_manager.mark_rate_limited("gemini", api_key, cooldown_seconds=120)
        raise


def generate_with_tools(
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> tuple[str, Optional[dict]]:
    if settings.llm_provider == "groq":
        try:
            return _groq_with_tools(
                system_prompt, user_message, tools, temperature, max_tokens
            )
        except Exception as e:
            err = str(e).lower()
            if "rate_limit" in err or "429" in err or "tokens per day" in err:
                logger.warning("Groq rate limited (tools), falling back to Gemini")
                try:
                    return _gemini_with_tools(
                        system_prompt, user_message, tools, temperature, max_tokens
                    )
                except Exception as e2:
                    logger.error(f"Gemini tools fallback failed: {e2}")
                    return (
                        "The AI service is temporarily rate-limited. Please try again in a few minutes.",
                        None,
                    )
            raise
    return _gemini_with_tools(
        system_prompt, user_message, tools, temperature, max_tokens
    )
