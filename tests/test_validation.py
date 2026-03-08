from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from selector_dsl.validation import validate_selector_payload  # noqa: E402


def test_validation_rejects_empty_composition() -> None:
    res = validate_selector_payload({"dsl_version": "0.1", "selector": {}})
    assert not res.ok


def test_validation_rejects_invalid_operator() -> None:
    payload = {
        "dsl_version": "0.1",
        "selector": {"all_of": [{"graph": "structural", "where": {"x": {"bogus": 1}}}]},
    }
    res = validate_selector_payload(payload)
    assert not res.ok
    assert any("invalid operator" in e for e in res.errors)


def test_validation_rejects_invalid_regex() -> None:
    payload = {
        "dsl_version": "0.1",
        "selector": {"all_of": [{"graph": "structural", "where": {"x": {"matches": "("}}}]},
    }
    res = validate_selector_payload(payload)
    assert not res.ok
    assert any("invalid regex" in e for e in res.errors)
