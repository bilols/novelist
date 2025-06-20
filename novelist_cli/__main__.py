"""
Minimal CLI:
    novelist init           # interactive wizard
    novelist generate       # non-interactive (mainly for test automation)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print

from novelist_cli.llm.openai_wrapper import call_llm
from novelist_cli.generators.prompt_builders import (
    build_outline_prompt,
    build_styleguide_prompt,
)

app = typer.Typer(pretty_exceptions_show_locals=False)

ARTIFACTS_DIR = Path.cwd() / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def _yesNo(prompt: str, default: bool = False) -> bool:
    resp = typer.prompt(prompt + (" [Y/n]" if default else " [y/N]")).lower()
    return (resp == "" and default) or resp.startswith("y")


@app.command()
def init(
    model: str = typer.Option(
        "gpt-4o-mini", help="OpenAI model name (cost visible after each call)"
    ),
    dry_run: bool = typer.Option(
        False, help="Skip actual OpenAI calls, just show estimated cost."
    ),
):
    """Launches a simple question-and-answer wizard; writes two JSON files."""

    print("[bold cyan]--- Novelist Outline & StyleGuide Wizard ---[/]\n")

    title = typer.prompt("Working title")
    genre = typer.prompt("Genre (e.g. Western, Sci-Fi)")
    mc_archetype = typer.prompt("Main-character archetype (e.g. Reluctant Hero)")
    tone = typer.prompt("Overall tone (e.g. gritty, hopeful)")
    words_total = typer.prompt("Target novel length (words)", default="60000")
    chapter_count = typer.prompt("Number of chapters", default="20")
    beats_per_chap = typer.prompt("Beats per chapter", default="4")
    depth = _yesNo("Seed sub-plots for each chapter?", default=False)
    famous = typer.prompt("Emulate famous author? (blank to skip)", default="")

    voice = typer.prompt("Narrative voice", default="third-person limited")
    tense = typer.prompt("Tense", default="past")
    sent_len = typer.prompt("Sentence length preference", default="moderate")
    lex_dens = typer.prompt("Lexical density", default="moderate")

    outline_inputs = {
        "title": title,
        "genre": genre,
        "target_length": int(words_total),
        "chapter_count": int(chapter_count),
        "beats_per_chapter": int(beats_per_chap),
        "depth_enabled": depth,
        "mc_archetype": mc_archetype,
        "tone": tone,
        "famous_style": famous or None,
    }

    style_inputs = {
        "voice": voice,
        "tense": tense,
        "sentence_length": sent_len,
        "lexical_density": lex_dens,
        "famous_style": famous or None,
    }

    # ----- call LLM -------------------------------------------------------
    outline_json = call_llm(
        model=model,
        messages=build_outline_prompt(outline_inputs),
        temperature=0.4,
        dry_run=dry_run,
    )

    style_json = call_llm(
        model=model,
        messages=build_styleguide_prompt(style_inputs),
        temperature=0.3,
        dry_run=dry_run,
    )

    if dry_run:
        print("[yellow]Dry-run complete – nothing written.[/]")
        raise typer.Exit()

    # ----- write files ----------------------------------------------------
    (ARTIFACTS_DIR / "novelist_outline.json").write_text(outline_json, encoding="utf-8")
    (ARTIFACTS_DIR / "novelist_style_guide.json").write_text(
        style_json, encoding="utf-8"
    )

    print(f"[green]✔ Outline and style guide saved to {ARTIFACTS_DIR}[/]")


@app.command()
def generate(
    config_file: Path = typer.Argument(..., exists=True),
    model: str = typer.Option("gpt-4o-mini"),
):
    """
    Non-interactive generation: pass a .json file containing the same
    input keys used in the wizard.  Handy for scripted tests.
    """
    cfg = json.loads(config_file.read_text(encoding="utf-8"))

    outline_json = call_llm(
        model=model,
        messages=build_outline_prompt(cfg["outline"]),
        temperature=0.4,
    )
    style_json = call_llm(
        model=model,
        messages=build_styleguide_prompt(cfg["style"]),
        temperature=0.3,
    )
    from novelist_cli.utils.validate import validate_outline, validate_style

    validate_outline(outline_json)
    validate_style(style_json)

    (ARTIFACTS_DIR / "novelist_outline.json").write_text(outline_json, encoding="utf-8")
    (ARTIFACTS_DIR / "novelist_style_guide.json").write_text(
        style_json, encoding="utf-8"
    )

    print(f"[green]✔ Files written to {ARTIFACTS_DIR}[/]")


if __name__ == "__main__":
    app()
