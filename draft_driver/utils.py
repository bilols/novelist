#!/usr/bin/env python3
"""
utils.py  –  shared helpers (v1.2)
• Dynamic max-token calculation
• Context vs completion limits kept separate
"""

from __future__ import annotations
import openai, logging, importlib

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
MODEL_DEFAULT = "gpt-4o"

CTX_LIMIT = {
    "gpt-3.5-turbo":        16_385,
    "gpt-3.5-turbo-16k":    16_385,
    "gpt-4":                 8_192,
    "gpt-4-0613":            8_192,
    "gpt-4o-mini":          32_768,
    "gpt-4o":              128_000,
    "gpt-4.1":              65_536,
    "gpt-4.1-mini":         32_768,
    "gpt-4.1-nano":         16_384,
    "gpt-4-turbo":         128_000,
    "gpt-4-turbo-preview": 128_000,
    "gpt-4.5-preview":     128_000,
}

COMP_LIMIT = {
    "gpt-4o-mini": 4096,
    "gpt-4o":      4096,
    "gpt-4-turbo": 4096,
    "gpt-4-turbo-preview": 4096,
    "gpt-4.5-preview": 4096,
    # defaults fall back to 4096
}

DEFAULT_COMP = 4096         # safe fallback

# optional tiktoken length helper
_tk = importlib.util.find_spec("tiktoken")
if _tk:
    import tiktoken
    enc_cache: dict[str,tiktoken.Encoding] = {}
    def tk_len(model: str, msgs: list[dict]) -> int:
        enc = enc_cache.setdefault(model, tiktoken.encoding_for_model(model))
        return sum(len(enc.encode(m["content"])) for m in msgs)
else:
    def tk_len(model: str, msgs: list[dict]) -> int:
        # rough: 0.7 words ≈ 1 token
        words = sum(len(m["content"].split()) for m in msgs)
        return int(words / 0.7)

# --------------------------------------------------------------------------
def cap_for(model: str) -> int:
    """Return completion cap for model (defaults to 4 096)."""
    return COMP_LIMIT.get(model, DEFAULT_COMP)

def safe_tokens(model: str, requested: int | None, min_words: int | None,
                used_prompt_tokens: int) -> int:
    """
    Decide a max_tokens value:
      • if `requested` provided use it (after clamping)
      • else derive from min_words (~0.7 words per token)
    """
    cap   = cap_for(model)
    if requested is None and min_words:
        requested = int(min_words / 0.7) + 50       # + buffer
    requested = requested or 2048                   # default if everything None
    margin = int(cap * 0.9)                         # 90 %
    return max(100, min(margin, requested, cap - used_prompt_tokens))

# --------------------------------------------------------------------------
def chat(model: str,
         messages: list[dict],
         requested_tokens: int | None = None,
         min_words: int | None = None):
    """
    Call OpenAI Chat API with a safe max_tokens value.
    """
    prompt_tok = tk_len(model, messages)
    max_tok    = safe_tokens(model, requested_tokens, min_words, prompt_tok)
    logger.debug("prompt=%d  max_tokens=%d  model=%s", prompt_tok, max_tok, model)

    resp = openai.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tok
    )
    return resp.choices[0].message.content
