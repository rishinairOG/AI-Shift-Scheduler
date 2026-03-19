"""
Shared OpenRouter LLM client with timeout, error classification, and Q&A logging.
All RAG modules should import get_llm() and log_qa_interaction() from here.
"""

import json
import os
import pathlib
from datetime import datetime, timezone

from langchain_openai import ChatOpenAI

_LOGS_DIR = pathlib.Path(__file__).resolve().parents[2] / "logs"

FRIENDLY_ERRORS = {
    "auth": (
        "Authentication failed — check that OPENROUTER_API_KEY is valid. "
        "Get a key at https://openrouter.ai"
    ),
    "rate_limit": (
        "Rate limit reached on OpenRouter. Wait a minute and try again."
    ),
    "timeout": (
        "The AI service took too long to respond. Try a shorter question or try again later."
    ),
    "connection": (
        "Could not reach the AI service. Check your internet connection."
    ),
    "generic": (
        "Something went wrong with the AI service. Try again shortly."
    ),
}


def get_llm(temperature: float = 0.1, max_tokens: int = 512) -> ChatOpenAI:
    """Return a ChatOpenAI pointed at OpenRouter with sensible defaults."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=temperature,
        max_tokens=max_tokens,
        request_timeout=30,
    )


def classify_llm_error(exc: Exception) -> str:
    """Map an LLM/HTTP exception to a FRIENDLY_ERRORS key."""
    msg = str(exc).lower()
    if "401" in msg or "unauthorized" in msg or "invalid api key" in msg:
        return "auth"
    if "429" in msg or "rate limit" in msg or "too many requests" in msg:
        return "rate_limit"
    if "timeout" in msg or "timed out" in msg:
        return "timeout"
    if "connection" in msg or "resolve" in msg or "unreachable" in msg:
        return "connection"
    return "generic"


def friendly_error_message(exc: Exception) -> str:
    """Return a user-facing message for an LLM-related exception."""
    return FRIENDLY_ERRORS[classify_llm_error(exc)]


def log_qa_interaction(
    question: str,
    answer: str,
    source: str = "policy_qa",
    extra: dict | None = None,
) -> None:
    """Append a Q&A interaction to logs/policy_qa.jsonl."""
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = _LOGS_DIR / "policy_qa.jsonl"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "question": question,
        "answer": answer,
    }
    if extra:
        entry["extra"] = extra
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
