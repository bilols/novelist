# 🐍 Novelist Pipeline (draft_v1)

An experimental Python workflow that turns a high‑level outline and style guide into a **full first‑draft novel**, then stitches the chapters, summaries, and epilogue into a clean manuscript.  
Powered by the OpenAI Chat Completions API.

> **Current milestone:** end‑to‑end draft generation (≈ 68 000 words) with model tagging, per‑chapter summaries, optional digest, and markdown manuscript builder.

---

## 1 What it does

```
outline/style‑guide  ─▶  draft_driver.py
                     │       ├─ chats with GPT (N chapters + epilogue)
                     │       ├─ saves   outputs/chapters/   *.md
                     │       ├─ saves   outputs/summaries/ *.summary.json
                     │       └─ logs progress + beat warnings
                     └▶  build_manuscript.py
                             ├─ concatenates chapters
                             ├─ optional digest of summaries
                             └─ writes outputs/final/manuscript.md
```

* **draft_driver.py** – Generates each chapter in *pieces* (default 8) with an inline piece marker for safe length control, tags the heading with the model used, then strips those markers before saving.  Produces a 120–150‑word summary + 5 factual key‑value pairs for every chapter (and the epilogue).

* **build_manuscript.py** – Reads `outputs/chapters/`, builds a title page with per‑chapter word counts and total, splices in all chapters (and epilogue), optionally appends a digest of chapter summaries, then formats via `engine/formatter.py`.

---

## 2 Quick start

```bash
git clone <repo>
cd novelist/draft_v1
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt                   # openai, python-dotenv, etc.

export OPENAI_API_KEY="sk-..."                    # Windows: set OPENAI_API_KEY=...
python -m engine.draft_driver --chapters 1        # generate first chapter
python -m engine.draft_driver                     # full 24‑chapter run + epilogue
python -m engine.draft_driver --epilogue-only     # only epilogue (needs summaries)

python -m engine.build_manuscript --with-digest   # compile manuscript.md

open outputs/final/manuscript.md
```

---

## 3 `draft_driver` CLI flags

| Flag | Example | Description |
|------|---------|-------------|
| `--start`      | `--start 10` | Begin at chapter 10 (resume). |
| `--chapters`   | `--chapters 3` | Limit generation to *n* chapters. |
| `--min-words`  | `--min-words 2500` | Minimum word count per chapter. |
| `--pieces`     | `--pieces 10` | Number of piece markers per chapter. |
| `--model`      | `--model gpt-4-turbo` | Override default model (`gpt-4o-mini`). Supported: `gpt-4o-mini`, `gpt-4o`, `gpt-4`, `gpt-4-turbo`, `gpt-4.5-preview`, `gpt-3.5-turbo`. |
| `--epilogue-only` |  | Skip chapters and generate epilogue from latest summary. |
| `--log-level`  | `--log-level DEBUG` | `DEBUG`, `INFO`, `WARNING`, etc. |

---

## 4 Project layout

```
draft_v1/
│
├─ inputs/
│   ├─ novelist_outline.json      ← 24‑chapter outline + epilogue (manual now)
│   └─ novelist_style_guide.json  ← Style and formatting rules
│
├─ engine/
│   ├─ draft_driver.py            ← Main generator
│   ├─ summarizer.py              ← 150‑word chapter summary + fact extractor
│   ├─ build_manuscript.py        ← Assemble Markdown book
│   ├─ formatter.py               ← Simple Markdown prettifier
│   ├─ utils.py                   ← OpenAI wrapper & token safety
│   ├─ logconf.py                 ← Logging helper
│   └─ __init__.py
│
└─ outputs/
    ├─ chapters/    ch01.md, …, epilogue.md
    ├─ summaries/   ch01.summary.json, …
    └─ final/       manuscript.md
```

---

## 5 Known limitations / roadmap

| Area | Status / TODO |
|------|---------------|
| Beat validation | Logs *possible* misses only—no auto rewrite yet. |
| Blackboard facts | Collected but not yet reused to steer next chapter. |
| Outline / style‑guide generation | Manual now; slated for **Phase 3** auto‑generator UI. |
| Editor chain | Dev‑, line‑, copy‑assistant pipeline is Phase 2. |
| Token limits | Completion clamped to 90 % of per‑model cap (4 096 for many). |
| Formats | Manuscript builder outputs Markdown; no EPUB/PDF hook yet. |

---

## 6 Change global default model

Edit **`engine/utils.py`**

```python
MODEL_DEFAULT = "gpt-4o-mini"
```

or simply pass `--model` at runtime.

---

Happy drafting!
