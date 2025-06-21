"""
Schema-validation helpers + light post-processing.

Usage (inside other modules):
    from novelist_cli.utils.validate import validate_outline, validate_style
    validate_outline(json_text)      # raises jsonschema.ValidationError on failure
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import jsonschema
from importlib import resources as pkg


# ─── internal helper ─────────────────────────────────────────────────────
def _maybe_unwrap(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLMs sometimes wrap the real payload:

        {"novelist_outline": { ... }}

    Accept that pattern and unwrap it.  Otherwise return the object as-is.
    """
    if (
        isinstance(obj, dict)
        and len(obj) == 1
        and next(iter(obj)) in {"novelist_outline", "outline", "novelist_style_guide"}
    ):
        return next(iter(obj.values()))
    return obj


def _load_schema(name: str) -> Dict[str, Any]:
    text = pkg.files("schemas").joinpath(name).read_text(encoding="utf-8")
    return json.loads(text)


# ─── public API ──────────────────────────────────────────────────────────
_outline_schema = _load_schema("outline.schema.json")
_style_schema = _load_schema("style_guide.schema.json")


def validate_outline(json_text: str) -> None:
    data = _maybe_unwrap(json.loads(json_text))
    jsonschema.validate(data, _outline_schema)


def validate_style(json_text: str) -> None:
    data = _maybe_unwrap(json.loads(json_text))
    jsonschema.validate(data, _style_schema)
