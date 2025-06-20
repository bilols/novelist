#!/usr/bin/env python3
"""
draft_driver.py – generate chapters & epilogue
v1.7  • --model flag  • heading shows model used
"""

import json, pathlib, argparse, re, os, logging
from dotenv import load_dotenv
import openai
from .logconf import init
from . import utils, summarizer

# ── CLI -------------------------------------------------------------------
p = argparse.ArgumentParser()
p.add_argument("--start", type=int, default=1, help="first chapter number")
p.add_argument("--chapters", type=int, help="limit chapters (excl. epilogue)")
p.add_argument("--min-words", type=int, default=2200)
p.add_argument("--pieces", type=int, default=8)
p.add_argument("--epilogue-only", action="store_true",
               help="skip chapters and only generate epilogue")
p.add_argument("--model", default=None,
               help="GPT model name (e.g. gpt-4, gpt-4o, gpt-4-turbo…)")
p.add_argument("--log-level", default="INFO")
args = p.parse_args()

init(args.log_level)
logger = logging.getLogger(__name__)

# ── Model selection -------------------------------------------------------
MODEL = args.model or utils.MODEL_DEFAULT
logger.info("Using model: %s", MODEL)

# ── Paths -----------------------------------------------------------------
ROOT   = pathlib.Path(__file__).resolve().parents[1]   # draft_v1/
INPUTS = ROOT / "inputs"
OUT    = ROOT / "outputs"
CHDIR  = OUT / "chapters";   CHDIR.mkdir(parents=True, exist_ok=True)
SUMDIR = OUT / "summaries";  SUMDIR.mkdir(parents=True, exist_ok=True)
STYLE_JSON = (INPUTS / "novelist_style_guide.json").read_text("utf-8")

# ── OpenAI ----------------------------------------------------------------
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY") or logger.critical("Missing OPENAI_API_KEY") or exit()

# ── Outline ---------------------------------------------------------------
outline  = json.loads((INPUTS / "novelist_outline.json").read_text("utf-8"))
chapters = sorted(outline["chapters"], key=lambda c: c["num"])
if args.chapters:
    chapters = chapters[: args.chapters]

# ── Helpers ---------------------------------------------------------------
PIECE_RE = re.compile(r"\[C(\d{2})-P\d]")
def remove_markers(t:str) -> str: return PIECE_RE.sub("", t).strip()
def ends_clean(t:str) -> bool:    return t.rstrip().endswith((".", "?”", "!”", "\""))
def beat_check(ch):               return "## Beat Checklist\n" + "\n".join(f"- ☐ {b}" for b in ch["beats"])
def write_and_log(name, text):
    CHDIR.joinpath(name).write_text(text, "utf-8")
    logger.info("%s saved (%d words)", name, len(text.split()))

def tag_heading(md: str, tag: str) -> str:
    """append (tag) to first-level heading if not already present"""
    def repl(m):
        hdr = m.group(0)
        return hdr if tag in hdr else f"{hdr} ({tag})"
    return re.sub(r"^#\s*(Chapter|Epilogue)[^\n]+", repl, md, count=1, flags=re.M)

# ── Initial summary -------------------------------------------------------
prev_summary = "Book opens here."
if args.epilogue_only:
    latest = sorted(SUMDIR.glob("ch??.summary.json"))[-1]
    prev_summary = json.loads(latest.read_text("utf-8"))["summary"]
    chapters = []        # skip chapter loop

# ── Chapter loop ----------------------------------------------------------
for ch in chapters:
    if ch["num"] < args.start:
        prev_summary = json.loads((SUMDIR / f"ch{ch['num']:02d}.summary.json").read_text())["summary"]
        continue

    logger.info("=== Chapter %02d ===", ch["num"])
    piece_marker = f"[C{ch['num']:02d}-P<x>]"
    target_words = int(args.min_words * 1.2)

    messages = [
        {"role":"system","content":STYLE_JSON},
        {"role":"system","content":"CHAPTER_OUTLINE:\n"+json.dumps(ch,indent=2)},
        {"role":"system","content":beat_check(ch)},
        {"role":"user","content":f"Previous chapter summary:\n{prev_summary}"},
        {"role":"user","content":f"""
Write Chapter {ch['num']:02d} titled "{ch['title']}" in {args.pieces} pieces.
Each piece starts with {piece_marker}.  Minimum {args.min_words} words (aim {target_words}).
Begin with "# Chapter {ch['num']:02d} – {ch['title']}"
After covering a beat, replace ☐ with ✔.  No meta commentary.
""".strip()}
    ]

    draft = utils.chat(MODEL, messages, 6000)

    # ensure min words
    if len(draft.split()) < args.min_words:
        tail = " ".join(draft.split()[-120:])
        draft += "\n" + utils.chat(
            MODEL,
            [{"role":"user","content":
              f'Continue after:\n"""{tail}"""\nWrite until ≥ {args.min_words} words.'}],
            1200)

    for _ in range(3):
        if ends_clean(draft): break
        draft += " " + utils.chat(MODEL,
            [{"role":"user","content":"Finish the current sentence."}], 400)

    # tag heading with model name
    draft = tag_heading(draft, MODEL)
    clean = remove_markers(draft)
    write_and_log(f"ch{ch['num']:02d}.md", clean)

    # relaxed beat validation
    miss = [b for b in ch["beats"] if not re.search(re.escape(b), clean, re.I)]
    if miss:
        logger.info("Beats maybe not covered: %s", miss)

    prev_summary, _ = summarizer.summarise_and_extract(clean)
    SUMDIR.joinpath(f"ch{ch['num']:02d}.summary.json").write_text(
        json.dumps({"summary": prev_summary}, indent=2), "utf-8"
    )

# ── Epilogue --------------------------------------------------------------
if "epilogue" in outline and (args.epilogue_only or not args.chapters or args.chapters >= len(chapters)+1):
    epi = outline["epilogue"]
    logger.info("=== Epilogue ===")

    epi_msg = [
        {"role":"system","content":STYLE_JSON},
        {"role":"system","content":"EPILOGUE_OUTLINE:\n"+json.dumps(epi,indent=2)},
        {"role":"user","content":f"Complete summary of preceding chapter:\n{prev_summary}"},
        {"role":"user","content":f"""
Write the Epilogue titled "{epi['title']}" in 2 pieces.
Begin with "# Epilogue – {epi['title']}"
Target 1 000–1 200 words.  Follow the outline faithfully.  No meta commentary.
""".strip()}
    ]

    draft = utils.chat(MODEL, epi_msg, 4000)
    for _ in range(3):
        if ends_clean(draft): break
        draft += " " + utils.chat(MODEL,
            [{"role":"user","content":"Finish the epilogue scene."}], 400)

    draft = tag_heading(draft, MODEL)
    clean = remove_markers(draft)
    write_and_log("epilogue.md", clean)

    epi_summary, _ = summarizer.summarise_and_extract(clean)
    SUMDIR.joinpath("epilogue.summary.json").write_text(
        json.dumps({"summary": epi_summary}, indent=2), "utf-8"
    )
    logger.info("Epilogue summary %d words", len(epi_summary.split()))

logger.info("Draft pipeline finished ✅")
