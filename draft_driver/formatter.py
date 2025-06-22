#!/usr/bin/env python3
"""
formatter.py — simple markdown cleaner usable as module or CLI
"""

import re, sys, pathlib

def smart_quotes(t:str) -> str:
    return (t.replace("“", '"').replace("”", '"')
              .replace("‘", "'").replace("’", "'"))

def normalize_dashes(t:str) -> str:
    return t.replace("—", "--").replace("–", "-")

def format_text(txt: str) -> str:
    txt = re.sub(r"\n{3,}", "\n\n", txt)           # collapse blank lines
    txt = re.sub(r"[ \t]+\n", "\n", txt)           # strip trailing spaces
    txt = smart_quotes(txt)
    txt = normalize_dashes(txt)
    return txt.strip() + "\n"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python -m engine.formatter FILE.md")
    p = pathlib.Path(sys.argv[1])
    p.write_text(format_text(p.read_text("utf-8")), "utf-8")
    print(f"✓ cleaned {p}")
