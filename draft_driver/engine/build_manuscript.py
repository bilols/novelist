#!/usr/bin/env python3
"""
Assemble manuscript from draft_v1/outputs/chapters/.
Option --with-digest appends all summaries.
"""

import re, sys, json, argparse
from pathlib import Path
from . import formatter            # relative import

# ── CLI -------------------------------------------------------------------
cli = argparse.ArgumentParser()
cli.add_argument("--with-digest", action="store_true")
args = cli.parse_args()

# ── Paths (project root = parent of 'engine') -----------------------------
ROOT   = Path(__file__).resolve().parents[1]     # draft_v1/
OUT    = ROOT / "outputs";  OUT.mkdir(exist_ok=True)
CHDIR  = OUT / "chapters"
SUMDIR = OUT / "summaries"
FINAL  = OUT / "final";     FINAL.mkdir(exist_ok=True)
DEST   = FINAL / "manuscript.md"

# ── Outline meta ----------------------------------------------------------
outline = json.loads((ROOT / "inputs" / "novelist_outline.json").read_text("utf-8"))
title  = outline.get("title", "Untitled")
author = outline.get("author", "")

# ── Gather chapter & epilogue files ---------------------------------------
chap_files = sorted(CHDIR.glob("ch??.md"))
epi_file   = CHDIR / "epilogue.md"
if epi_file.exists():
    chap_files.append(epi_file)

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

# ── Optional digest -------------------------------------------------------
digest = ""
if args.with_digest:
    summaries = []
    for js in sorted(SUMDIR.glob("*.summary.json")):
        summaries.append(json.loads(js.read_text("utf-8"))["summary"].strip())
    digest = "\n\n---\n\n## Digest (all summaries)\n\n" + "\n\n".join(summaries)

# ── Title page & combine --------------------------------------------------
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
print(f"✅ Manuscript created → {DEST}  ({total:,} words)")
