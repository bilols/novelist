"""
openai-python ≥1.0 compatible wrapper
"""

from __future__ import annotations

import dotenv, os; dotenv.load_dotenv()
import os
import time
from pathlib import Path
from typing import List, Dict, Any

from openai import OpenAI  # ← new style
from rich import print

# ─── token price table (USD / 1K tokens) ──────────────────────────────────
_COST = {
    "gpt-4o-mini": 0.0005,
    "gpt-4o": 0.005,
    "gpt-4-turbo": 0.003,
    "gpt-4.5-preview": 0.01,
}
_LOG_FILE = Path.home() / ".novelist_costs.csv"
if not _LOG_FILE.exists():
    _LOG_FILE.write_text("ts,model,prompt_tokens,completion_tokens,cost\n", encoding="utf-8")

# ─── client instance (reads OPENAI_API_KEY env var) ───────────────────────
client = OpenAI()


def _log_cost(model: str, p: int, c: int) -> None:
    cost = (p + c) / 1000 * _COST.get(model, 0.0)
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{int(time.time())},{model},{p},{c},{cost:.6f}\n")
    print(f"[grey50][LLM] {model}  p={p}  c={c}  →  ${cost:.4f}[/]")


def call_llm(
    *,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int | None = None,
    dry_run: bool = False,
) -> str:
    """
    Execute a chat completion and return the assistant's message text.

    `dry_run=True` prints cost estimate and returns "" without calling the API.
    """

    if dry_run:
        char_len = sum(len(m["content"]) for m in messages)
        print(f"[yellow][dry-run] Would call {model} with ~{char_len} characters[/]")
        return ""

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    usage = response.usage  # prompt_tokens, completion_tokens
    _log_cost(model, usage.prompt_tokens, usage.completion_tokens)

    return response.choices[0].message.content
