#!/usr/bin/env python3
"""
build_manuscript.py  –  stitch chapter / prologue / epilogue files
into a single Markdown manuscript.

Designed to be called via the Poetry script:
  novelist-build = "draft_driver.build_manuscript:main"
"""

from __future__ import annotations

import argparse
import logging
import pathlib
import re
import shutil
import sys
from typing import List

from .logconf import init

# ────────────────────────────────────────────────────────────────────────────
ROOT  = pathlib.Path(__file__).resolve().parent
OUT   = ROOT.parent / "outputs"
CHDIR = OUT / "chapters"
FINAL = OUT / "final"; FINAL.mkdir(exist_ok=True)

ORDER_RE = re.compile(r"^# (?:Prologue|Chapter (\d+)|Epilogue)", re.I)

# ----------------------------------------------------------------------------
def chapter_sort_key(path: pathlib.Path) -> tuple[int, str]:
    """Sort Prologue → numeric chapters → Epilogue."""
    text = path.read_text("utf-8", errors="ignore").splitlines()[0]
    m = ORDER_RE.match(text.strip())
    if not m:
        return (sys.maxsize, str(path))
    num = m.group(1)
    if text.lower().startswith("# prologue"):
        return (0, "")
    if text.lower().startswith("# epilogue"):
        return (10_000, "")
    return (int(num), "")

# ----------------------------------------------------------------------------
def build_manuscript(min_chapters: int | None = None) -> pathlib.Path:
    """Return path of the compiled manuscript."""
    parts: List[pathlib.Path] = sorted(CHDIR.glob("*.md"), key=chapter_sort_key)
    if min_chapters and len(parts) < min_chapters:
        raise RuntimeError(f"Only {len(parts)} chapters present; expected ≥{min_chapters}")

    manuscript = FINAL / "manuscript.md"
    with manuscript.open("w", encoding="utf-8") as out:
        for p in parts:
            out.write(p.read_text("utf-8"))
            out.write("\n\n")

    # Also copy to top‑level convenience location, overwriting silently
    shutil.copy2(manuscript, OUT / "manuscript.md")
    return manuscript

# ----------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Concatenate generated .md files into a manuscript.")
    p.add_argument("--require", type=int, metavar="N",
                   help="fail if fewer than N chapter files are present")
    p.add_argument("--log-level", default="INFO")
    return p

# ----------------------------------------------------------------------------
def main(argv: List[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    init(args.log_level)
    logger = logging.getLogger("manuscript_builder")

    try:
        m_path = build_manuscript(args.require)
        word_count = len(m_path.read_text("utf-8").split())
        logger.info("Manuscript created → %s  (%s words)", m_path, f"{word_count:,}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Manuscript build failed: %s", exc)
        sys.exit(1)

# ----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
