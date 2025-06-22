# engine/summarizer.py
"""
Summariser that returns (summary_text, facts_dict).

FACTS fenced block schema:
{
  "characters_added":   ["Name"],
  "characters_updated": { "Name": {"status":"alive"} },
  "locations_added":    ["Place"],
  "threads_added":      [],
  "threads_resolved":   []
}
"""

import json, textwrap, re, logging, openai
from .utils import chat, MODEL_DEFAULT

logger = logging.getLogger(__name__)

FACT_RE = re.compile(r"```FACTS\s*(\{.*?})\s*```", re.S)

def summarise_and_extract(chapter_text: str, max_words: int = 150):
    """Return (summary_string, facts_dict). facts_dict may be {} on failure."""
    prompt = textwrap.dedent(f"""
        Summarise the chapter in 120-{max_words} words.
        Then append a JSON object that lists ONLY new or updated facts,
        using this exact fenced format:

        ```FACTS
        {{
          "characters_added":   [],
          "characters_updated": {{
            "Caleb Langtry": {{"status":"alive"}}
          }},
          "locations_added":    [],
          "threads_added":      [],
          "threads_resolved":   []
        }}
        ```

        Return the prose summary, a blank line, then the ```FACTS block.
    """)

    raw = chat(
        MODEL_DEFAULT,
        [
            {"role": "user", "content": prompt},
            {"role": "user", "content": chapter_text},
        ],
        900,
    )

    m = FACT_RE.search(raw)
    if not m:
        logger.error("FACTS block missing; returning empty facts.")
        summary = raw.strip()
        facts   = {}
    else:
        summary = raw[: m.start()].strip()
        try:
            facts = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            logger.error("Malformed FACTS JSON: %s", e)
            facts = {}

    # Hard-trim summary to max_words
    words = summary.split()
    if len(words) > max_words:
        summary = " ".join(words[:max_words])

    logger.info("Summary %d words | FACT keys: %d",
                len(summary.split()), len(facts))

    return summary, facts
