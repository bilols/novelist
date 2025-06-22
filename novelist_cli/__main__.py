"""
Wizard v5.4 – multi-pass outline generator
 • CLI flags: --config PATH, --save-prompts
 • Robust JSON-parsing retries (empty or spurious output handled)

Bill © 2025
"""

from __future__ import annotations
import datetime as dt, json, math, re, textwrap
from pathlib import Path
from typing import Dict, List

import typer
from rich import print
from jsonschema import validate as _validate, ValidationError

from novelist_cli.llm.openai_wrapper import call_llm
from novelist_cli.utils.validate import validate_outline, validate_style

ROOT = Path.cwd()
ART_DIR = ROOT / "artifacts"; ART_DIR.mkdir(exist_ok=True)

# ─────────────────── load master schema ──────────────────────────────────
SCHEMA_CHAPTERS = json.loads((ROOT / "schemas" / "chapters.schema.json").read_text())
BASE_DEFS = SCHEMA_CHAPTERS["definitions"]

# ─── build relaxed schema for single blocks (num≥0) ──────────────────────
_props = json.loads(json.dumps(BASE_DEFS["chapterCore"]["properties"]))
_props["num"]["minimum"] = 0
_SC_SINGLE = {
    "type": "object",
    "required": ["num", "title", "pov", "beats"],
    "properties": _props,
    "definitions": {               # keep $refs valid            # NEW
        "beat": BASE_DEFS["beat"],
        "chapterCore": BASE_DEFS["chapterCore"],
    },
}
SCHEMA_PROLOGUE = _SC_SINGLE
SCHEMA_EPILOGUE = _SC_SINGLE

# ─────────────── runtime constants ───────────────────────────────────────
BATCH_SIZE = 6
MAX_ATTEMPTS_PER_CALL = 3

# ═════════ helper loaders ═════════
def _load_genres() -> List[str]:
    return json.loads((ROOT / "presets" / "genres.json").read_text())


def _load_presets() -> List[Dict]:
    out = []
    for p in (ROOT / "presets" / "styles").glob("*.json"):
        data = json.loads(p.read_text())
        out.append({"path": p, "name": data.get("name", p.stem), "data": data})
    return out


def _collect_list(title: str, pre: List[str] | None) -> List[str]:
    if pre is not None:
        return pre
    print(f"\n[i]{title}[/] (blank → finish)")
    lst: List[str] = []
    while True:
        line = input("> ").strip()
        if not line:
            break
        lst.append(line)
    return lst


def _beats_block(beats: int, tw: int, depth: bool) -> str:
    sub = '["<string>"]' if depth else "[]"
    tpl = '{{ "summary": "<string>", "target_words": %d, "sub_plots": %s }}' % (tw, sub)
    return ",\n        ".join([tpl] * beats)


def _chapter_stub(n: int, bb: str) -> str:
    return (
        "    {\n"
        f'      "num": {n},\n'
        '      "title": "<string>",\n'
        '      "pov": "<string>",\n'
        '      "beats": [\n'
        f"        {bb}\n"
        "      ]\n"
        "    }"
    )


def _build_prompt(
    meta: Dict,
    done: List[Dict],
    idx: List[int],
    beats_pc: int,
    tw: int,
    depth: bool,
    label: str | None,
) -> List[Dict]:
    bb = _beats_block(beats_pc, tw, depth)
    block = (
        f'"{label}": ' + _chapter_stub(idx[0], bb)
        if label
        else '"chapters": [\n' + ",\n".join(_chapter_stub(i, bb) for i in idx) + "\n  ]"
    )
    stub = "{\n  " + block + "\n}"

    s_msg = textwrap.dedent(
        """
        You are ChapterArchitect-GPT.

        • Use FROZEN_METADATA & CHAPTERS_SO_FAR as context (read-only).
        • Fill every <string> placeholder.
        • Do NOT change array sizes.
        • Output *only* valid JSON (no markdown).
        """
    ).strip()

    u_msg = (
        "FROZEN_METADATA:\n"
        + json.dumps(meta, indent=2, ensure_ascii=False)
        + "\n\nCHAPTERS_SO_FAR:\n"
        + json.dumps(done, indent=2, ensure_ascii=False)
        + "\n\nWRITABLE_STUB:\n"
        + stub
    )

    return [
        {"role": "system", "content": s_msg},
        {"role": "user", "content": u_msg, "response_format": {"type": "json_object"}},
    ]


# ═════════════════════ wizard CLI ═════════════════════
app = typer.Typer(pretty_exceptions_show_locals=False)


@app.callback(invoke_without_command=True)
def wizard(
    ctx: typer.Context,
    gen_model: str = typer.Option("gpt-4o"),
    gen_temp: float = typer.Option(0.25),
    config: Path | None = typer.Option(None, "--config"),
    save_prompts: bool = typer.Option(False, "--save-prompts/--no-save-prompts"),
):
    if ctx.invoked_subcommand:
        return

    cfg: Dict = json.loads(config.read_text()) if config else {}
    if cfg:
        print(f"[yellow]Loaded answers from {config}[/]")

    def ans(key: str, prompt: str, default=None):
        return cfg[key] if key in cfg else typer.prompt(prompt, default=default)

    print("[bold cyan]─── Novelist Wizard (multi-pass) ───[/]\n")

    # ① basics
    title = ans("title", "Title")
    author = ans("author", "Author")
    premise = ans("premise", "Premise (≤150 words)")
    genres = _load_genres()
    genre = (
        cfg["genre"]
        if "genre" in cfg
        else genres[int(typer.prompt("\nGenre number (0 custom)", "12")) - 1]
    )
    tgt_words = int(ans("novel_target_words", "Target words", "60000"))
    chapters = int(ans("chapters", "Chapters", "20"))
    beats_pc = int(ans("beats_per_chapter", "Beats per chapter", "4"))
    depth = cfg.get("depth_enabled") if "depth_enabled" in cfg else typer.confirm("Seed sub-plots?", False)
    inc_pro = cfg.get("include_prologue") if "include_prologue" in cfg else typer.confirm("Include prologue?", False)
    inc_epi = cfg.get("include_epilogue") if "include_epilogue" in cfg else typer.confirm("Include epilogue?", False)

    # ② characters etc.
    chars = cfg.get("main_characters") or []
    if not chars and typer.confirm("\nAdd characters now?", False):
        while True:
            nm = typer.prompt(" Character (blank=done)", "").strip()
            if not nm:
                break
            role = typer.prompt("  Role")
            traits = _collect_list("  Traits", None)
            arc = typer.prompt("  Arc (blank ok)", "")
            chars.append({"name": nm, "role": role, "traits": traits, "arc": arc})

    events = _collect_list("Timeline key events", cfg.get("timeline_key_events"))
    themes = _collect_list("Thematic notes / motifs", cfg.get("thematic_notes"))
    cont = _collect_list("Continuity checklist", cfg.get("continuity_checklist"))
    special = cfg.get("special_instructions") or typer.prompt("\nSpecial instructions (blank ok)", "")

    # ③ style preset
    presets = _load_presets()
    if "style_preset_name" in cfg:
        want = cfg["style_preset_name"].lower()
        preset = next(p["data"] for p in presets if p["name"].lower() == want)
    else:
        print("\n[i]Choose style preset:[/]")
        for i, p in enumerate(presets, 1):
            print(f" {i}. {p['name']}")
        preset = presets[int(typer.prompt("Number")) - 1]["data"]

    # ④ metadata
    meta = dict(
        title=title,
        author=author,
        revision_date=dt.datetime.utcnow().isoformat() + "Z",
        premise=premise,
        genre=genre,
        novel_target_words=tgt_words,
        main_characters=chars,
        timeline_key_events=events,
        thematic_notes=themes,
        continuity_checklist=cont,
        special_instructions=special,
    )
    wpb = math.ceil(tgt_words / chapters / beats_pc)
    outline: Dict = {"chapters": []}

    def dump(obj, tag):
        ts = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        (ART_DIR / f"{tag}_{ts}.json").write_text(
            json.dumps(obj, indent=2, ensure_ascii=False) if isinstance(obj, (dict, list)) else str(obj)
        )

    # ⑤ batch runner
    def run_batch(ix: List[int], label: str | None, rnd: int):
        schema = (
            SCHEMA_PROLOGUE if label == "prologue" else
            SCHEMA_EPILOGUE if label == "epilogue" else
            SCHEMA_CHAPTERS
        )
        for attempt in range(1, MAX_ATTEMPTS_PER_CALL + 1):
            msgs = _build_prompt(meta, outline["chapters"], ix, beats_pc, wpb, depth, label)
            if save_prompts and attempt == 1:
                dump(msgs, f"prompt_round{rnd}")
            raw = call_llm(model=gen_model, messages=msgs, temperature=gen_temp).strip()

            # ── sanitise ---------------------------------------------------  # NEW
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", raw, flags=re.S).strip()
            if raw and not raw.lstrip().startswith("{"):
                brace = raw.find("{")
                raw = raw[brace:] if brace != -1 else ""
            if not raw:
                print(f"[red]JSON parse round{rnd} attempt{attempt}: empty response[/]")
                continue
            # ----------------------------------------------------------------

            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                dump(raw, f"badjson_round{rnd}_attempt{attempt}")
                print(f"[red]JSON parse round{rnd} attempt{attempt}: {e}[/]")
                continue
            try:
                _validate(data[label] if label else data, schema)
            except ValidationError as e:
                dump(data, f"badschema_round{rnd}_attempt{attempt}")
                print(f"[red]Schema error round{rnd} attempt{attempt}: {e}[/]")
                continue
            if label:
                outline[label] = data[label]
            else:
                outline["chapters"].extend(data["chapters"])
            return
        raise RuntimeError(f"Batch {ix} failed after {MAX_ATTEMPTS_PER_CALL} attempts.")

    # ⑥ generation loop
    rnd = 0
    if inc_pro:
        rnd += 1; run_batch([0], "prologue", rnd)

    indexes = list(range(1, chapters + 1))
    for i in range(0, len(indexes), BATCH_SIZE):
        rnd += 1; run_batch(indexes[i : i + BATCH_SIZE], None, rnd)

    if inc_epi:
        rnd += 1; run_batch([999], "epilogue", rnd)

    # ⑦ save
    full_outline = {**meta, **outline}
    validate_outline(json.dumps(full_outline)); validate_style(json.dumps(preset))
    (ART_DIR / "novelist_outline.json").write_text(json.dumps(full_outline, indent=2, ensure_ascii=False))
    (ART_DIR / "novelist_style_guide.json").write_text(json.dumps(preset, indent=2, ensure_ascii=False))
    print(f"[green]✔ Outline & style guide saved to {ART_DIR}[/]")


if __name__ == "__main__":
    app()
