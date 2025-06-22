#!/usr/bin/env python3
"""
Assemble manuscript from outputs/chapters/.
Reads outline from artifacts/ if available, otherwise inputs/.  
Use --with-digest to append all summaries.
"""

import re, sys, json, argparse
from pathlib import Path
from . import formatter

# ── CLI -------------------------------------------------------------------
cli = argparse.ArgumentParser()
cli.add_argument("--with-digest", action="store_true")
args = cli.parse_args()

# ── Paths -----------------------------------------------------------------
ROOT  = Path(__file__).resolve().parents[1]
ART   = ROOT / "artifacts"
INP   = ROOT / "inputs"

OUT   = ROOT / "outputs";  OUT.mkdir(exist_ok=True)
CHDIR = OUT / "chapters"
SUMDIR= OUT / "summaries"
FINAL = OUT / "final";     FINAL.mkdir(exist_ok=True)
DEST  = FINAL / "manuscript.md"

# ── Outline ---------------------------------------------------------------
outline_path = (ART / "novelist_outline.json") if (ART / "novelist_outline.json").exists() \
               else (INP / "novelist_outline.json")
outline = json.loads(outline_path.read_text("utf-8"))
title   = outline.get("title","Untitled")
author  = outline.get("author","")

# ── Gather chapters -------------------------------------------------------
chap_files = sorted(CHDIR.glob("ch??.md"))
if (CHDIR / "prologue.md").exists():
    chap_files.insert(0, CHDIR / "prologue.md")
if (CHDIR / "epilogue.md").exists():
    chap_files.append(CHDIR / "epilogue.md")

if not chap_files:
    sys.exit("❌  No chapter files found in outputs/chapters/")

word_re, parts, wc_table, total = re.compile(r"\w+"), [], [], 0
for fp in chap_files:
    txt   = fp.read_text("utf-8").strip()
    words = len(word_re.findall(txt))
    total += words
    wc_table.append((fp.stem, words))
    parts.append(txt)
    print(f"✓ {fp.name:<17} {words:,} words")

# ── Optional digest --------------------------------------------------------
digest = ""
if args.with_digest:
    summaries = []
    for js in sorted(SUMDIR.glob("*.summary.json")):
        summaries.append(json.loads(js.read_text("utf-8"))["summary"].strip())
    digest = "\n\n---\n\n## Digest (all summaries)\n\n" + "\n\n".join(summaries)

# ── Title page & combine ---------------------------------------------------
title_pg = [
    f"# {title}",
    f"**Author:** {author}" if author else "",
    "",
    "## Word Counts",
    *[f"- {stem}: {w:,} words" for stem, w in wc_table],
    f"\n**Total:** {total:,} words",
    "\n---\n"
]

manuscript = "\n".join(title_pg) + ("\n\n***\n\n".join(parts)) + digest + "\n"
manuscript = formatter.format_text(manuscript)
DEST.write_text(manuscript, "utf-8")
print(f"✅  Manuscript created → {DEST}  ({total:,} words)")
