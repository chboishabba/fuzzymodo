from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from selector_dsl.norms import apply_norm_constraints  # noqa: E402


def test_norm_constraint_stale_detection() -> None:
    nc = {
        "id": "NC-1",
        "dsl_version": "0.1",
        "selector": {
            "all_of": [
                {"graph": "structural", "where": {"function.name": {"eq": "parse"}}}
            ]
        },
        "assertion": {"kind": "design_intent", "statement": "x"},
        "effect": {"mode": "prune", "bug_classes": ["type_mismatch"]},
        "provenance": {"decided_by": "a", "decided_at": "t", "rationale": "r"},
    }

    facts = {"structural": {"function.name": "other"}}
    ann = apply_norm_constraints([nc], facts=facts)
    assert ann.applied == []
    assert ann.stale_constraints == ["NC-1"]


def test_norm_constraint_applies_when_matching() -> None:
    nc = {
        "id": "NC-2",
        "dsl_version": "0.1",
        "selector": {
            "any_of": [
                {"graph": "threat", "where": {"cwe.id": {"in": [79]}}},
            ]
        },
        "assertion": {"kind": "design_intent", "statement": "x"},
        "effect": {"mode": "escalate", "bug_classes": ["encoding_violation"]},
        "provenance": {"decided_by": "a", "decided_at": "t", "rationale": "r"},
    }

    facts = {"threat": {"cwe.id": 79}}
    ann = apply_norm_constraints([nc], facts=facts)
    assert ann.stale_constraints == []
    assert len(ann.applied) == 1
    assert ann.applied[0].constraint_id == "NC-2"
    assert ann.applied[0].mode == "escalate"
