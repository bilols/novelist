#!/usr/bin/env python3
"""
build_manuscript.py – stitch Prologue / Chapters / Epilogue
into a single, cleaned Markdown manuscript (only one file produced).
"""

from __future__ import annotations

import argparse
import json
import logging
import pathlib
import re
import sys
from typing import List

from .logconf import init
from .formatter import format_text          # text normaliser

ROOT  = pathlib.Path(__file__).resolve().parent
ART   = ROOT.parent / "artifacts"
CHDIR = ART / "chapters"
FINAL = ART / "final"; FINAL.mkdir(exist_ok=True)
META  = ART / "draft_stats.json"

ORDER_RE   = re.compile(r"^# (?:Prologue|Chapter (\d+)|Epilogue)", re.I)
PAGE_BREAK = "\n\n\f\n\n"                  # \f = page break

# ----------------------------------------------------------------------
def chapter_sort_key(path: pathlib.Path) -> tuple[int, str]:
    first = path.read_text("utf-8", errors="ignore").splitlines()[0]
    m = ORDER_RE.match(first.strip())
    if not m:
        return (sys.maxsize, str(path))
    if first.lower().startswith("# prologue"):
        return (0, "")
    if first.lower().startswith("# epilogue"):
        return (10_000, "")
    return (int(m.group(1)), "")

# ----------------------------------------------------------------------
def build_front_page() -> str | None:
    if not META.exists():
        logging.warning("draft_stats.json not found – summary page skipped.")
        return None

    meta = json.loads(META.read_text("utf-8"))
    lines = [
        meta.get("book_title", "UNTITLED").upper(),
        meta.get("author_name", "Unknown Author"),
        "",
        f"Generated using OpenAI model: {meta.get('model', '?')}",
        "",
    ]

    chaps = sorted(
        (p for p in meta["parts"] if p["type"] == "chapter"),
        key=lambda x: x.get("num", 0)
    )
    for c in chaps:
        lines.append(f"{c['title']} ({c['word_count']:,})")

    lines.append("")
    total = sum(p["word_count"] for p in meta["parts"])
    lines.append(f"Total words: {total:,}")
    return "\n".join(lines)

# ----------------------------------------------------------------------
def build_manuscript(require: int | None = None) -> pathlib.Path:
    parts = sorted(CHDIR.glob("*.md"), key=chapter_sort_key)
    if require and len(parts) < require:
        raise RuntimeError(f"Only {len(parts)} parts found; expected ≥{require}")

    text_fragments: list[str] = []
    front = build_front_page()
    if front:
        text_fragments.append(front)
        text_fragments.append(PAGE_BREAK)

    for p in parts:
        text_fragments.append(p.read_text("utf-8"))
        text_fragments.append("\n\n")

    cleaned = format_text("".join(text_fragments))
    manu = FINAL / "manuscript.md"
    manu.write_text(cleaned, "utf-8")
    return manu

# ----------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Create cleaned manuscript.md")
    p.add_argument("--require", type=int, metavar="N",
                   help="fail if fewer than N parts exist")
    p.add_argument("--log-level", default="INFO")
    return p

# ----------------------------------------------------------------------
def main(argv: List[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    init(args.log_level)
    logger = logging.getLogger("manuscript_builder")

    try:
        m = build_manuscript(args.require)
        wc = len(m.read_text("utf-8").split())
        logger.info("Manuscript created → %s  (%s words)", m, f"{wc:,}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Build failed: %s", exc)
        sys.exit(1)

if __name__ == "__main__":
    main()
