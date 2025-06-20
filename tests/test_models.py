# tests/test_models.py
import json
from pathlib import Path
import jsonschema
from novelist_cli.models import Outline, Chapter, ChapterBeat

SCHEMAS = Path(__file__).parents[1] / "schemas"

def test_outline_roundtrip():
    sample = Outline(
        title="Demo",
        genre="SF",
        target_length=60000,
        chapters=[
            Chapter(
                number=1,
                title="Arrival",
                beats=[ChapterBeat(summary="Hook", target_words=500)]
            )
        ],
    )
    raw = sample.model_dump()
    jsonschema.validate(raw, json.loads((SCHEMAS / "outline.schema.json").read_text()))
