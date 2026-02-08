from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from selector_dsl.evaluator import evaluate_selector  # noqa: E402


def test_all_of_any_of_not_composition() -> None:
    selector = {
        "dsl_version": "0.1",
        "selector": {
            "all_of": [
                {"graph": "structural", "where": {"function.name": {"eq": "parse_text"}}},
            ],
            "any_of": [
                {"graph": "threat", "where": {"cwe.id": {"in": [79, 89]}}},
                {"graph": "execution", "where": {"crash.cluster": {"exists": True}}},
            ],
            "not": {"graph": "normative", "where": {"decision.kind": {"eq": "allow"}}},
        },
    }
    facts = {
        "structural": {"function.name": "parse_text"},
        "threat": {"cwe.id": 79},
        "normative": {"decision.kind": "review"},
    }
    assert evaluate_selector(selector, facts)


def test_operator_matrix() -> None:
    selector = {
        "selector": {
            "all_of": [
                {
                    "graph": "execution",
                    "where": {
                        "count": {"gt": 1, "lt": 10},
                        "entry": {"startswith": "api_"},
                        "path": {"matches": r"^/v[0-9]+/"},
                        "decision": {"neq": "deny"},
                    },
                }
            ]
        }
    }
    facts = {
        "execution": {
            "count": 5,
            "entry": "api_parse",
            "path": "/v2/parser",
            "decision": "review",
        }
    }
    assert evaluate_selector(selector, facts)


def test_exists_false_and_invalid_regex_fail() -> None:
    selector_exists = {
        "selector": {
            "all_of": [
                {"graph": "structural", "where": {"missing.field": {"exists": False}}},
            ]
        }
    }
    assert evaluate_selector(selector_exists, {"structural": {"function.name": "x"}})

    selector_regex = {
        "selector": {
            "all_of": [
                {"graph": "structural", "where": {"function.name": {"matches": "("}}},
            ]
        }
    }
    assert not evaluate_selector(selector_regex, {"structural": {"function.name": "parse"}})


def test_rejects_empty_composition() -> None:
    assert not evaluate_selector({"selector": {}}, {})

