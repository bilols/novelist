"""
novelist_cli.__main__
Command-line entry-point for the Novelist toolbox.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List

import typer
from rich import print

from novelist_cli.generators.prompt_builders import (
    build_outline_prompt,
    build_styleguide_prompt,
)
from novelist_cli.llm.openai_wrapper import call_llm
from novelist_cli.utils.validate import validate_outline, validate_style

# ───────────────────────────── CLI setup ────────────────────────────────
app = typer.Typer(pretty_exceptions_show_locals=False)
ARTIFACTS_DIR = Path.cwd() / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def _yes_no(prompt: str, default: bool = False) -> bool:
    resp = typer.prompt(prompt + (" [Y/n]" if default else " [y/N]")).lower()
    return (resp == "" and default) or resp.startswith("y")


# ───────────────────── helper : retry wrapper ───────────────────────────
def _generate_with_retry(
    *,
    builder: Callable[[Dict[str, Any]], List[Dict[str, Any]]],
    validator: Callable[[str], None],
    inputs: Dict[str, Any],
    file_name: str,
    model: str,
    temperature: float,
    dry_run: bool,
    max_attempts: int,
) -> str:
    for attempt in range(1, max_attempts + 1):
        result = call_llm(
            model=model,
            messages=builder(inputs),
            temperature=temperature,
            dry_run=dry_run,
        )
        if dry_run:
            return ""
        try:
            validator(result)
            return result
        except Exception as err:
            print(
                f"[red]Validation error {attempt}/{max_attempts} for {file_name}: "
                f"{err}[/]"
            )
    raise RuntimeError(f"Failed after {max_attempts} attempts: {file_name}")


# ──────────────────────── interactive wizard ────────────────────────────
@app.command()
def init(
    model: str = typer.Option("gpt-4o-mini", help="OpenAI model"),
    dry_run: bool = typer.Option(False, help="Skip API calls; show cost only"),
    max_attempts: int = typer.Option(5, help="Retries on schema failure"),
    outline_temp: float = typer.Option(0.15, help="Temperature for outline"),
    style_temp: float = typer.Option(0.35, help="Temperature for style guide"),
):
    """Interactive outline & style-guide generator."""

    print("[bold cyan]--- Novelist Wizard ---[/]\n")

    # ── core story info ──────────────────────────────────────────────────
    title = typer.prompt("Working title")
    premise = typer.prompt(
        "One-sentence premise (blank → auto-create)", default=""
    ).strip()

    if premise == "":
        premise = call_llm(
            model=model,
            messages=[
                {"role": "system", "content": "You are a log-line generator."},
                {
                    "role": "user",
                    "content": f"Give me a one-sentence premise for a horror novel titled '{title}'.",
                },
            ],
            temperature=0.7,
            max_tokens=60,
        ).strip()
        print(f"[green]Premise auto-generated:[/] {premise}")

    genre = typer.prompt("Genre (e.g. Western, Sci-Fi)")
    mc_archetype = typer.prompt("Main-character archetype")
    tone = typer.prompt("Overall tone")
    words_total = int(typer.prompt("Target novel length (words)", default="60000"))
    chapter_count = int(typer.prompt("Number of chapters", default="20"))
    beats_per_chapter = int(typer.prompt("Beats per chapter", default="4"))
    depth = _yes_no("Seed sub-plots for each beat?", default=False)
    famous = typer.prompt("Emulate famous author? (blank to skip)", default="")

    # ── style settings ──────────────────────────────────────────────────
    voice = typer.prompt("Narrative voice", default="third-person limited")
    tense = typer.prompt("Tense", default="past")

    allowed_len = {"short", "moderate", "long"}
    sl_raw = typer.prompt("Sentence length (short / moderate / long)", default="moderate")
    sentence_len = sl_raw.lower().strip()
    if sentence_len not in allowed_len:
        print(
            f"[yellow]⚠ '{sl_raw}' not allowed → using 'moderate'.[/]"
        )
        sentence_len = "moderate"

    allowed_den = {"low", "moderate", "high"}
    ld_raw = typer.prompt("Lexical density (low / moderate / high)", default="moderate")
    lexical_den = ld_raw.lower().strip()
    if lexical_den not in allowed_den:
        print(
            f"[yellow]⚠ '{ld_raw}' not allowed → using 'moderate'.[/]"
        )
        lexical_den = "moderate"

    # ── build input dicts ───────────────────────────────────────────────
    outline_inputs = {
        "title": title,
        "premise": premise,
        "genre": genre,
        "target_length": words_total,
        "chapter_count": chapter_count,
        "beats_per_chapter": beats_per_chapter,
        "depth_enabled": depth,
        "mc_archetype": mc_archetype,
        "tone": tone,
        "famous_style": famous or None,
    }

    style_inputs = {
        "voice": voice,
        "tense": tense,
        "sentence_length": sentence_len,
        "lexical_density": lexical_den,
        "famous_style": famous or None,
    }

    # ── generate & validate outline ─────────────────────────────────────
    outline_json = _generate_with_retry(
        builder=build_outline_prompt,
        validator=validate_outline,
        inputs=outline_inputs,
        file_name="novelist_outline.json",
        model=model,
        temperature=outline_temp,
        dry_run=dry_run,
        max_attempts=max_attempts,
    )

    # ── generate & validate style guide ─────────────────────────────────
    style_json = _generate_with_retry(
        builder=build_styleguide_prompt,
        validator=validate_style,
        inputs=style_inputs,
        file_name="novelist_style_guide.json",
        model=model,
        temperature=style_temp,
        dry_run=dry_run,
        max_attempts=max_attempts,
    )

    if dry_run:
        print("[yellow]Dry-run complete – no files written.[/]")
        raise typer.Exit()

    # ── write artifacts ────────────────────────────────────────────────
    (ARTIFACTS_DIR / "novelist_outline.json").write_text(
        outline_json, encoding="utf-8"
    )
    (ARTIFACTS_DIR / "novelist_style_guide.json").write_text(
        style_json, encoding="utf-8"
    )
    print(f"[green]✔ Saved to {ARTIFACTS_DIR}[/]")


# ───────────────────── non-interactive runner ───────────────────────────
@app.command()
def generate(
    config_file: Path = typer.Argument(..., exists=True),
    model: str = typer.Option("gpt-4o-mini"),
):
    """Generate from a JSON config file (outline + style keys)."""
    cfg = json.loads(config_file.read_text(encoding="utf-8"))

    outline_json = call_llm(
        model=model,
        messages=build_outline_prompt(cfg["outline"]),
        temperature=0.15,
    )
    style_json = call_llm(
        model=model,
        messages=build_styleguide_prompt(cfg["style"]),
        temperature=0.35,
    )

    (ARTIFACTS_DIR / "novelist_outline.json").write_text(
        outline_json, encoding="utf-8"
    )
    (ARTIFACTS_DIR / "novelist_style_guide.json").write_text(
        style_json, encoding="utf-8"
    )
    print(f"[green]✔ Files written to {ARTIFACTS_DIR}[/]")


# ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app()
