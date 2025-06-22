"""
Prompt builders v4 (unchanged)
• Pre-allocates every chapter placeholder.
• Model may write only <string> fields.
• Optional prologue / epilogue.
"""

from __future__ import annotations
import json, math
from textwrap import dedent
from typing import Any, Dict, List


def _words_per_beat(total: int, chaps: int, beats: int) -> int:
    return math.ceil(total / chaps / beats)


def _beats_block(beats: int, tw: int, depth: bool) -> str:
    sub = '["<string>"]' if depth else "[]"
    tpl = '{{ "summary": "<string>", "target_words": %d, "sub_plots": %s }}' % (tw, sub)
    return ",\n        ".join([tpl] * beats)


def _chapter_stub(num: int, bb: str) -> str:
    return (
        "    {\n"
        f'      "num": {num},\n'
        '      "title": "<string>",\n'
        '      "pov": "<string>",\n'
        '      "beats": [\n'
        f"        {bb}\n"
        "      ]\n"
        "    }"
    )


def build_chapter_prompt(meta: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    wpb = _words_per_beat(meta["novel_target_words"], cfg["chapter_count"], cfg["beats_per_chapter"])
    bb  = _beats_block(cfg["beats_per_chapter"], wpb, cfg["depth_enabled"])

    chapters = ",\n".join([_chapter_stub(i, bb) for i in range(1, cfg["chapter_count"] + 1)])
    stub = "{\n  \"chapters\": [\n" + chapters + "\n  ]"
    if cfg["include_prologue"]:
        stub += ",\n  \"prologue\": " + _chapter_stub(0, bb)
    if cfg["include_epilogue"]:
        stub += ",\n  \"epilogue\": " + _chapter_stub(999, bb)
    stub += "\n}"

    sys_msg = dedent(
        f"""
        You are ChapterArchitect-GPT.
        * FROZEN_METADATA is read-only.
        * Replace <string> placeholders ONLY.
        * Do not change array lengths: {cfg['chapter_count']} chapters, {cfg['beats_per_chapter']} beats each.
        * If depth_enabled=true every beats[*].sub_plots must hold ≥1 string.
        """
    ).strip()

    user_msg = (
        "FROZEN_METADATA:\n"
        + json.dumps(meta, ensure_ascii=False, indent=2)
        + "\n\nWRITABLE_STUB:\n"
        + stub
    )

    return [
        {"role": "system", "content": sys_msg},
        {"role": "user",   "content": user_msg, "response_format": {"type": "json_object"}},
    ]
