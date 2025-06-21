# scripts/validate_artifacts.py
"""
Validate the JSON files produced by `novelist init` against their schemas.

Usage (from repo root):
    poetry run python scripts/validate_artifacts.py
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
from rich import print

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
SCHEMAS = ROOT / "schemas"


def validate_file(json_path: Path, schema_path: Path) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)
    print(f"[green]✔ {json_path.name} is valid.[/]")


def main() -> None:
    try:
        validate_file(
            ARTIFACTS / "novelist_outline.json",
            SCHEMAS / "outline.schema.json",
        )
        validate_file(
            ARTIFACTS / "novelist_style_guide.json",
            SCHEMAS / "style_guide.schema.json",
        )
    except jsonschema.ValidationError as e:
        print(f"[red]❌ Validation failed:[/]\n{e.message}\n\nPath: {list(e.path)}")
    except FileNotFoundError as e:
        print(f"[yellow]⚠ File missing:[/]\n{e.filename}")


if __name__ == "__main__":
    main()
