#!/usr/bin/env python3
"""
build_manuscript.py – stitch chapter / prologue / epilogue files
into a single Markdown manuscript in ./artifacts/final/
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

ROOT = pathlib.Path(__file__).resolve().parent
ART  = ROOT.parent / "artifacts"
CHDIR = ART / "chapters"
FINAL = ART / "final"; FINAL.mkdir(exist_ok=True)

ORDER_RE = re.compile(r"^# (?:Prologue|Chapter (\d+)|Epilogue)", re.I)


def chapter_sort_key(path: pathlib.Path) -> tuple[int, str]:
    """Sort order: Prologue → chapter N → Epilogue."""
    first = path.read_text("utf-8", errors="ignore").splitlines()[0]
    m = ORDER_RE.match(first.strip())
    if not m:
        return (sys.maxsize, str(path))
    if first.lower().startswith("# prologue"):
        return (0, "")
    if first.lower().startswith("# epilogue"):
        return (10_000, "")
    return (int(m.group(1)), "")


def build_manuscript(require: int | None = None) -> pathlib.Path:
    parts = sorted(CHDIR.glob("*.md"), key=chapter_sort_key)
    if require and len(parts) < require:
        raise RuntimeError(f"Only {len(parts)} parts found; expected ≥{require}")

    manu = FINAL / "manuscript.md"
    with manu.open("w", encoding="utf-8") as out:
        for p in parts:
            out.write(p.read_text("utf-8"))
            out.write("\n\n")

    # convenience copy
    shutil.copy2(manu, ART / "manuscript.md")
    return manu


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Concatenate generated .md files into a manuscript.")
    p.add_argument("--require", type=int, metavar="N",
                   help="fail if fewer than N parts exist")
    p.add_argument("--log-level", default="INFO")
    return p


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
