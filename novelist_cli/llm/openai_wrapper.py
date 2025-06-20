"""
Thin convenience wrapper around openai.ChatCompletion with:

* unified interface (model, messages, **kwargs)
* automatic token-cost logging
* opt-in dry-run simulation for unit-tests

Usage:
    from novelist_cli.llm import call_llm

    resp_text = call_llm(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hi"}],
    )
"""

from __future__ import annotations

import dotenv, os; dotenv.load_dotenv()
import os
import time
from pathlib import Path
from typing import Any, List, Dict

import openai
from rich import print

# --- cost table (USD per 1K tokens) – keep up-to-date manually ------------
_COSTS = {
    "gpt-4o-mini": 0.0005,
    "gpt-4o": 0.005,
    "gpt-4-turbo": 0.003,
    "gpt-4.5-preview": 0.01,
}

# CSV log file in user profile
_COST_LOG = Path.home() / ".novelist_costs.csv"
_COST_LOG.write_text("timestamp,model,prompt_tokens,completion_tokens,cost\n", encoding="utf-8") if not _COST_LOG.exists() else None

# -------------------------------------------------------------------------


def _log_cost(model: str, prompt: int, completion: int) -> None:
    cost = (prompt + completion) / 1000 * _COSTS.get(model, 0)
    with _COST_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{int(time.time())},{model},{prompt},{completion},{cost:.6f}\n")
    print(f"[grey50][LLM] model={model} prompt={prompt} completion={completion} → ${cost:.4f}[/]")


def call_llm(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int | None = None,
    dry_run: bool = False,
) -> str:
    """
    Return assistant message.content as plain string.

    Set ``dry_run=True`` to bypass the API and return an empty string
    while still printing the would-have-been cost.
    """
    if dry_run:
        print(f"[yellow][dry-run] Would call {model} with {sum(len(m['content']) for m in messages)} chars[/]")
        return ""

    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    usage = response["usage"]  # type: ignore[index]
    _log_cost(model, usage["prompt_tokens"], usage["completion_tokens"])
    return response["choices"][0]["message"]["content"]  # type: ignore[index]
