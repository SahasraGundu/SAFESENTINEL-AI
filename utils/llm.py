"""
Thin wrapper around the Groq API.

If GROQ_API_KEY is not set, or the API call fails for any reason, every
function here degrades gracefully to a clearly-labeled rule-based
fallback rather than crashing the app or fabricating a "confident" AI
answer. This is important: nothing downstream should silently pretend
an LLM produced something it didn't.
"""
from __future__ import annotations

import json
from typing import Any

from utils.config import GROQ_API_KEY, GROQ_MODEL

_client = None
_client_error: str | None = None

if GROQ_API_KEY:
    try:
        from groq import Groq

        _client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:  # pragma: no cover - defensive
        _client_error = str(e)
else:
    _client_error = "GROQ_API_KEY not set"


def llm_available() -> bool:
    return _client is not None


def llm_status_message() -> str:
    if llm_available():
        return f"Connected to Groq ({GROQ_MODEL})"
    return f"LLM offline — {_client_error}. Using rule-based reasoning fallback."


def chat(system_prompt: str, user_prompt: str, json_mode: bool = False, max_tokens: int = 900) -> str | None:
    """Returns the raw text response, or None if the LLM is unavailable/fails."""
    if _client is None:
        return None
    try:
        kwargs: dict[str, Any] = dict(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        completion = _client.chat.completions.create(**kwargs)
        return completion.choices[0].message.content
    except Exception:
        return None


def chat_json(system_prompt: str, user_prompt: str, max_tokens: int = 900) -> dict | None:
    raw = chat(system_prompt, user_prompt, json_mode=True, max_tokens=max_tokens)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # one retry with an explicit correction instruction
        retry_prompt = (
            f"{user_prompt}\n\nYour previous response was not valid JSON. "
            "Return ONLY a valid JSON object, no prose, no markdown fences."
        )
        raw2 = chat(system_prompt, retry_prompt, json_mode=True, max_tokens=max_tokens)
        if raw2 is None:
            return None
        try:
            return json.loads(raw2)
        except (json.JSONDecodeError, TypeError):
            return None
