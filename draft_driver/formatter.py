#!/usr/bin/env python3
"""
formatter.py — lightweight Markdown cleaner

Usable both as a library (`from .formatter import format_text`)
and as a CLI:

    poetry run python -m novelist_cli.formatter path/to/file.md
"""

from __future__ import annotations

import re
import sys
import pathlib

__all__ = ["format_text"]

# ----------------------------------------------------------------------
def _smart_quotes(t: str) -> str:
    return (
        t.replace("“", '"').replace("”", '"')
         .replace("‘", "'").replace("’", "'")
    )

def _normalize_dashes(t: str) -> str:
    return t.replace("—", "--").replace("–", "-")

def _unify_eol(t: str) -> str:
    return t.replace("\r\n", "\n").replace("\r", "\n")


# ----------------------------------------------------------------------
def format_text(txt: str) -> str:
    """
    Return *txt* cleaned of common whitespace / Unicode oddities.

    Rules applied (in order):

    1. Convert CR/LF variants to `\\n`.
    2. Collapse 3+ consecutive blank lines -> 2 blank lines.
    3. Strip trailing spaces / tabs.
    4. Replace “smart quotes” with straight quotes.
    5. Replace em/en dashes with ASCII `--` / `-`.
    6. Ensure exactly one trailing newline at EOF.
    """
    txt = _unify_eol(txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)       # collapse blank paragraphs
    txt = re.sub(r"[ \t]+\n", "\n", txt)       # strip EOL whitespace
    txt = _smart_quotes(txt)
    txt = _normalize_dashes(txt)
    return txt.rstrip() + "\n"                 # canonical single newline


# ----------------------------------------------------------------------
def _cli() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: python -m novelist_cli.formatter FILE.md")
    p = pathlib.Path(sys.argv[1])
    p.write_text(format_text(p.read_text("utf-8")), "utf-8")
    print(f"✓ cleaned {p}")

if __name__ == "__main__":
    _cli()
