#!/usr/bin/env python3
"""
draft_driver.py – generate prologue, chapters & epilogue
v2.1.2 • don't rewrite outline unless encoding actually fixed
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
import re
import sys
from codecs import BOM_UTF8
from typing import Any, Dict, List

from dotenv import load_dotenv
import openai

from .logconf import init
from . import utils, summarizer


# ───────────────────────── helpers ──────────────────────────
def _read_json(path: pathlib.Path) -> Dict[str, Any]:
    """
    Read JSON regardless of encoding; rewrite as UTF‑8 **only if** encoding
    or BOM had to be fixed.  Prevents needless line‑ending churn.
    """
    encodings = [
        "utf-8",
        "utf-8-sig",
        sys.getfilesystemencoding(),
        "windows-1252",
        "latin-1",
    ]
    raw = path.read_bytes()
    for enc in encodings:
        try:
            txt = raw.decode(enc)
            json.loads(txt)             # validate
            break
        except (UnicodeDecodeError, json.JSONDecodeError):
            txt = None
    else:                               # fallback
        txt = raw.decode("latin-1", errors="ignore")
        logging.warning("%s decoded with latin-1 + ignore.", path.name)

    had_bom = txt.startswith(BOM_UTF8.decode())
    if had_bom:
        txt = txt.lstrip(BOM_UTF8.decode())

    # rewrite only if we really changed something
    if enc.lower() not in {"utf-8", "utf-8-sig"} or had_bom:
        path.write_text(txt, "utf-8")
        logging.info("Re‑saved %s as UTF‑8 (orig enc: %s, bom=%s)",
                     path.name, enc, had_bom)

    return json.loads(txt)


PIECE_RE   = re.compile(r"\[C(\d{2})-P\d]")
remove_markers = lambda t: PIECE_RE.sub("", t).strip()
ends_clean     = lambda t: t.rstrip().endswith((".", "?”", "!”", "\""))

def beat_check(ch: Dict[str, Any]) -> str:
    bullet = lambda b: b if isinstance(b, str) else b.get("summary", "")
    return "## Beat Checklist\n" + "\n".join("☐ " + bullet(b) for b in ch["beats"])


# ───────────────────────── arg‑parser ───────────────────────
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=int, default=1, help="first chapter number")
    p.add_argument("--chapters", type=int, help="limit chapters")
    p.add_argument("--min-words", type=int, default=2200)
    p.add_argument("--pieces", type=int, default=8)
    p.add_argument("--epilogue-only", action="store_true")
    p.add_argument("--model", default=None)
    p.add_argument("--log-level", default="INFO")
    return p


# ───────────────────────── main pipeline ────────────────────
def main(argv: List[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    init(args.log_level)
    logger = logging.getLogger("draft_driver")

    MODEL = args.model or utils.MODEL_DEFAULT
    logger.info("Using model: %s", MODEL)

    ROOT = pathlib.Path(__file__).resolve().parent
    ART  = ROOT.parent / "artifacts"
    OUT  = ROOT.parent / "outputs";  OUT.mkdir(exist_ok=True)
    CHDIR = OUT / "chapters";   CHDIR.mkdir(exist_ok=True)
    SUMDIR = OUT / "summaries"; SUMDIR.mkdir(exist_ok=True)

    outline = _read_json(ART / "novelist_outline.json")
    style   = _read_json(ART / "novelist_style_guide.json")
    STYLE_JSON = json.dumps(style, ensure_ascii=False, indent=2)

    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY") or \
        logger.critical("Missing OPENAI_API_KEY") or exit()

    chapters = sorted(outline["chapters"], key=lambda c: c["num"])
    if args.chapters:
        chapters = chapters[: args.chapters]

    def write(name: str, text: str):
        CHDIR.joinpath(name).write_text(text, "utf-8")
        logger.info("%s saved (%d words)", name, len(text.split()))

    prev_summary = "Novel opens here."

    # ── Prologue (optional) ─────────────────────────────────
    if "prologue" in outline and not args.epilogue_only:
        pro = outline["prologue"]
        logger.info("=== Prologue ===")
        msgs = [
            {"role": "system", "content": STYLE_JSON},
            {"role": "system", "content": "PROLOGUE_OUTLINE:\n" + json.dumps(pro, indent=2)},
            {"role": "user", "content": f"""
Write the Prologue “{pro['title']}” in 2 pieces,
start with "# Prologue – {pro['title']}",
1 000–1 200 words, cover all beats, no meta commentary.
"""},
        ]
        draft = utils.chat(MODEL, msgs, 4000)
        for _ in range(3):
            if ends_clean(draft):
                break
            draft += " " + utils.chat(MODEL, [{"role": "user", "content": "Finish the scene."}], 400)
        draft = remove_markers(draft)
        write("prologue.md", draft)
        prev_summary, _ = summarizer.summarise_and_extract(draft)
        SUMDIR.joinpath("prologue.summary.json").write_text(
            json.dumps({"summary": prev_summary}, indent=2), "utf-8"
        )

    # ── Chapter loop ───────────────────────────────────────
    if args.epilogue_only:
        last = sorted(SUMDIR.glob("ch??.summary.json"))[-1]
        prev_summary = json.loads(last.read_text("utf-8"))["summary"]
        chapters = []

    for ch in chapters:
        if ch["num"] < args.start:
            prev_summary = json.loads(
                (SUMDIR / f"ch{ch['num']:02d}.summary.json").read_text("utf-8")
            )["summary"]
            continue

        logger.info("=== Chapter %02d ===", ch["num"])
        target_words = int(args.min_words * 1.2)
        piece_tag = f"[C{ch['num']:02d}-P<x>]"

        messages = [
            {"role": "system", "content": STYLE_JSON},
            {"role": "system", "content": "CHAPTER_OUTLINE:\n" + json.dumps(ch, indent=2)},
            {"role": "system", "content": beat_check(ch)},
            {"role": "user",   "content": f"Prev-chapter summary:\n{prev_summary}"},
            {"role": "user",   "content": f"""
Write Chapter {ch['num']:02d} “{ch['title']}” in {args.pieces} pieces.
Each piece must start with {piece_tag}.  Goal ≈ {target_words} words (≥{args.min_words} absolute).
Begin with "# Chapter {ch['num']:02d} – {ch['title']}"
Replace ☒ with ✔ when a beat is fulfilled.  No meta commentary.
"""},
        ]

        draft = utils.chat(MODEL, messages, 6000)

        while len(draft.split()) < args.min_words:
            tail = " ".join(draft.split()[-120:])
            draft += " " + utils.chat(
                MODEL,
                [{"role": "user",
                  "content": f'Continue after:\n"""{tail}"""\nuntil ≥{args.min_words} words.'}],
                1200,
            )

        for _ in range(3):
            if ends_clean(draft):
                break
            draft += " " + utils.chat(MODEL, [{"role": "user", "content": "Finish the sentence."}], 400)

        draft = remove_markers(draft)
        write(f"ch{ch['num']:02d}.md", draft)

        prev_summary, _ = summarizer.summarise_and_extract(draft)
        SUMDIR.joinpath(f"ch{ch['num']:02d}.summary.json").write_text(
            json.dumps({"summary": prev_summary}, indent=2), "utf-8"
        )

    # ── Epilogue (optional) ────────────────────────────────
    if "epilogue" in outline and (
        args.epilogue_only
        or not args.chapters
        or args.chapters >= len(chapters) + 1
    ):
        epi = outline["epilogue"]
        logger.info("=== Epilogue ===")
        msgs = [
            {"role": "system", "content": STYLE_JSON},
            {"role": "system", "content": "EPILOGUE_OUTLINE:\n" + json.dumps(epi, indent=2)},
            {"role": "user", "content": f"Summary of previous material:\n{prev_summary}"},
            {"role": "user", "content": f"""
Write the Epilogue “{epi['title']}” in 2 pieces,
start with "# Epilogue – {epi['title']}",
1 000–1 200 words, cover all beats, no meta commentary.
"""},
        ]
        draft = utils.chat(MODEL, msgs, 4000)
        for _ in range(3):
            if ends_clean(draft):
                break
            draft += " " + utils.chat(MODEL, [{"role": "user", "content": "Finish the scene."}], 400)

        draft = remove_markers(draft)
        write("epilogue.md", draft)
        epi_sum, _ = summarizer.summarise_and_extract(draft)
        SUMDIR.joinpath("epilogue.summary.json").write_text(
            json.dumps({"summary": epi_sum}, indent=2), "utf-8"
        )

    logger.info("Draft pipeline finished ✅")


# ───────────────────────── entry‑point ─────────────────────
if __name__ == "__main__":
    main()
