"""
High-level helpers that take validated Outline / StyleGuide objects (or
their *input parameters*) and return the messages list expected by
openai.ChatCompletion.

The actual LLM call happens in openai_wrapper.call_llm().
"""

from __future__ import annotations

from typing import List, Dict, Any
from textwrap import dedent

# -------------------------------------------------------------------------


def build_outline_prompt(inputs: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    `inputs` is the dict returned by the Typer wizard –– already validated.

    Expected keys:
        title, genre, target_length, chapter_count, beats_per_chapter,
        depth_enabled, mc_archetype, tone, famous_style (optional)
    """
    sys_msg = dedent(
        f"""
        You are NovelOutliner-GPT, an expert in creating tight, scene-driven
        outlines that downstream agents will expand into chapters.

        • Output format MUST be JSON and match the provided schema names exactly.
        • Provide {inputs['chapter_count']} chapters, each with at least
          {inputs['beats_per_chapter']} beats.
        • The novel's target length is {inputs['target_length']} words
          ({inputs['target_length']//inputs['chapter_count']} per chapter).
        • Genre: {inputs['genre']}; target tone: {inputs['tone']}.
        • Main-character archetype: {inputs['mc_archetype']}.
        """
    ).strip()

    if inputs.get("famous_style"):
        sys_msg += f"\n• Emulate stylistic hallmarks of {inputs['famous_style']}."

    user_msg = (
        "Return only the JSON for `novelist_outline.json` – no preamble, "
        "no markdown ``` fences."
    )

    return [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": user_msg},
    ]


def build_styleguide_prompt(inputs: Dict[str, Any]) -> List[Dict[str, str]]:
    sys_msg = dedent(
        f"""
        You are StyleGuide-GPT.  Produce a concise JSON style guide
        compatible with Elements of Style, overridden as per user input.
        Voice: {inputs['voice']}, Tense: {inputs['tense']},
        Sentence length: {inputs['sentence_length']},
        Lexical density: {inputs['lexical_density']}.
        """
    ).strip()

    if inputs.get("famous_style"):
        sys_msg += f"\nInclude hallmarks reminiscent of {inputs['famous_style']}."

    user_msg = "Output JSON only for `novelist_style_guide.json`."

    return [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": user_msg},
    ]
