#!/usr/bin/env python3
"""
summarizer.py  – returns a concise prose summary of a chapter.

The former FACTS‑tracking block has been removed.  The public API is now:

    summary: str = summarizer.summarise(chapter_text, max_words=150)

Nothing else is returned.
"""

from __future__ import annotations

import logging
import textwrap

from .utils import chat, MODEL_DEFAULT

logger = logging.getLogger(__name__)


def summarise(chapter_text: str, max_words: int = 150) -> str:
    """
    Summarise *chapter_text* in ≤ *max_words* words.

    Returns
    -------
    str
        Pure prose summary with no lists, JSON, or code fences.
    """
    prompt = textwrap.dedent(
        f"""
        Summarise the chapter in 120‑{max_words} words.
        Return ONLY the prose summary.  Do not add lists, markdown,
        or any metadata – just narrative sentences.
        """
    ).strip()

    summary = chat(
        MODEL_DEFAULT,
        [
            {"role": "user", "content": prompt},
            {"role": "user", "content": chapter_text},
        ],
        requested_tokens=700,
    )

    # hard‑trim in case the model over‑shoots
    words = summary.split()
    if len(words) > max_words:
        summary = " ".join(words[:max_words])

    logger.info("Summarised to %d words", len(summary.split()))
    return summary
