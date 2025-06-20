# novelist_cli/utils/validate.py
import json, jsonschema, importlib.resources as pkg
from pathlib import Path

def validate_outline(json_text: str) -> None:
    schema = json.loads(pkg.files('schemas').joinpath('outline.schema.json').read_text())
    jsonschema.validate(json.loads(json_text), schema)

def validate_style(json_text: str) -> None:
    schema = json.loads(pkg.files('schemas').joinpath('style_guide.schema.json').read_text())
    jsonschema.validate(json.loads(json_text), schema)
