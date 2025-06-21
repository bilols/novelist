"""
novelist_cli.generators.prompt_builders

Builds `messages` lists for outline and style-guide generation, forcing
OpenAI to return exactly one JSON object via
`response_format={"type":"json_object"}`.
"""

from __future__ import annotations

from math import ceil
from textwrap import dedent
from typing import Any, Dict, List


# ───────────────────────── helpers ──────────────────────────
def _words_per_beat(total: int, chapters: int, beats: int) -> int:
    """Round up to avoid under-allocation."""
    return ceil(total / chapters / beats)


def _outline_stub(opts: Dict[str, Any]) -> str:
    """
    Skeleton containing two chapters, each with the exact
    beats_per_chapter beats.  All JSON braces are **doubled** so the
    later .format() call (for {num}) ignores them.
    """
    wpb = _words_per_beat(
        opts["target_length"], opts["chapter_count"], opts["beats_per_chapter"]
    )
    sub_plots = '["<string>"]' if opts["depth_enabled"] else "[]"

    # build one beat (percent-formatting keeps doubled braces intact)
    beat_tpl = '{{ "summary": "<string>", "target_words": %d, "sub_plots": %s }}' % (
        wpb,
        sub_plots,
    )
    beats_block = ",\n        ".join([beat_tpl] * opts["beats_per_chapter"])

    chapter_block = (
        "    {{\n"
        '      "number": {num},\n'
        '      "title": "<string>",\n'
        '      "beats": [\n'
        f"        {beats_block}\n"
        "      ]\n"
        "    }}"
    )

    chapters_stub = ",\n".join(
        [chapter_block.format(num=1), chapter_block.format(num=2)]
    )

    return (
        "{\n"
        '  "title": "<string>",\n'
        '  "genre": "<string>",\n'
        f'  "target_length": {opts["target_length"]},\n'
        '  "chapters": [\n'
        f"{chapters_stub}\n"
        "  ],\n"
        '  "metadata": {}\n'
        "}"
    ).strip()


_STYLE_STUB = """
{
  "voice": "<string>",
  "tense": "<past|present>",
  "sentence_length": "<short|moderate|long>",
  "lexical_density": "<low|moderate|high>",
  "tone": "<string>",
  "banned_cliches": ["<string>"],
  "rules": { "<guideline>": "<example or explanation>" }
}
""".strip()


# ───────────────────── outline prompt ──────────────────────
def build_outline_prompt(opts: Dict[str, Any]) -> List[Dict[str, Any]]:
    sys_msg = dedent(
        f"""
        You are NovelOutliner-GPT.
        • Produce **exactly {opts['chapter_count']} chapters**.
        • Each chapter must contain **exactly {opts['beats_per_chapter']} beats**.
        • If depth_enabled=true, every beats[*].sub_plots list must contain ≥1 string.
        • Premise: {opts['premise']}
        • MC archetype: {opts['mc_archetype']}
        Return ONE JSON object – no wrapper keys.
        """
    ).strip()

    if opts.get("famous_style"):
        sys_msg += f"\nEmulate subtle hallmarks of {opts['famous_style']}."

    user_msg = (
        "Fill the placeholders and repeat the chapter pattern until the array "
        f'length equals {opts["chapter_count"]}:\n{_outline_stub(opts)}'
    )

    return [
        {"role": "system", "content": sys_msg},
        {
            "role": "user",
            "content": user_msg,
            "response_format": {"type": "json_object"},
        },
    ]


# ────────────────── style-guide prompt ────────────────────
def build_styleguide_prompt(opts: Dict[str, Any]) -> List[Dict[str, Any]]:
    sys_msg = dedent(
        f"""
        You are StyleGuide-GPT. Replace ONLY the placeholders; keep keys identical.
        voice={opts['voice']}; tense={opts['tense']};
        sentence_length={opts['sentence_length']}; lexical_density={opts['lexical_density']}.
        """
    ).strip()

    if opts.get("famous_style"):
        sys_msg += f"\nBlend subtle traits of {opts['famous_style']}."

    user_msg = "Fill this JSON object:\n" + _STYLE_STUB

    return [
        {"role": "system", "content": sys_msg},
        {
            "role": "user",
            "content": user_msg,
            "response_format": {"type": "json_object"},
        },
    ]
