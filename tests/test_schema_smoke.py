"""Smoke checks for planning artifacts and selector scaffolding."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_selector_schema_loads() -> None:
    schema_path = ROOT / "docs/planning/fuzzymodo/selector_dsl.schema.json"
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    assert data["title"] == "Fuzzymodo Selector DSL"


def test_norm_constraint_schema_loads() -> None:
    schema_path = ROOT / "docs/planning/fuzzymodo/norm_constraint.schema.json"
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    assert data["title"] == "Fuzzymodo Norm Constraint"
