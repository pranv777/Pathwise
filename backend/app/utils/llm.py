"""Single place to construct the Gemini chat model used by every agent."""

from __future__ import annotations

import json
import re
from typing import Any

import json_repair
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from app.config import settings

_llms: dict[float, ChatGoogleGenerativeAI] = {}


def get_llm(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    """Lazily construct one Gemini chat model per temperature."""
    if temperature not in _llms:
        if not settings.google_api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Add it to backend/.env (see .env.example)."
            )
        _llms[temperature] = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            api_key=SecretStr(settings.google_api_key),
            temperature=temperature,
        )
    return _llms[temperature]


def response_text(response: BaseMessage) -> str:
    """Normalize an LLM response to plain text (content may be a str or a
    list of content blocks)."""
    content = response.content
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for part in content:
        if isinstance(part, str):
            parts.append(part)
        elif isinstance(part, dict) and part.get("type") == "text":
            parts.append(str(part.get("text", "")))
    return "".join(parts)


def extract_json(text: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object from an LLM response that may
    be wrapped in markdown fences, contain extra prose, or have minor syntax
    issues."""
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidate = (fence.group(1) if fence else text).strip()

    parsed: Any = None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\})", candidate, re.DOTALL)
        strict_candidate = match.group(1) if match else candidate
        try:
            parsed = json.loads(strict_candidate)
        except json.JSONDecodeError:
            parsed = json_repair.loads(strict_candidate)

    if not isinstance(parsed, dict) or not parsed:
        raise ValueError(f"Could not parse JSON object from LLM output: {text[:200]!r}")
    return parsed
