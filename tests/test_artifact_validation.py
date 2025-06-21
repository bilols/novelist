import json
from pathlib import Path
import jsonschema

ROOT = Path(__file__).parents[1]
ART = ROOT / "artifacts"
SCHEMA = ROOT / "schemas"

def _validate(name, schema_name):
    data = json.loads((ART / name).read_text())
    schema = json.loads((SCHEMA / schema_name).read_text())
    jsonschema.validate(data, schema)

def test_outline():
    _validate("novelist_outline.json", "outline.schema.json")

def test_style():
    _validate("novelist_style_guide.json", "style_guide.schema.json")
