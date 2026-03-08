from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from selector_dsl.canonical import selector_hash  # noqa: E402


def test_hash_deterministic_across_key_order() -> None:
    a = {"any_of": [{"graph": "structural", "where": {"x": {"eq": 1}}}]}
    b = {"any_of": [{"where": {"x": {"eq": 1}}, "graph": "structural"}]}
    assert selector_hash(a) == selector_hash(b)


def test_hash_normalizes_newlines_in_strings() -> None:
    a = {"all_of": [{"graph": "structural", "where": {"note": {"eq": "a\r\nb"}}}]}
    b = {"all_of": [{"graph": "structural", "where": {"note": {"eq": "a\nb"}}}]}
    assert selector_hash(a) == selector_hash(b)
