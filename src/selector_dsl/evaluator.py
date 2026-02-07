"""Selector evaluator scaffold.

Evaluation semantics are documented in
`docs/planning/fuzzymodo/selector_dsl_spec.md`.
"""

from __future__ import annotations

from typing import Any, Dict


def evaluate_selector(selector: Dict[str, Any], facts: Dict[str, Dict[str, Any]]) -> bool:
    """Evaluate selector against graph facts.

    This is a scaffold placeholder and currently supports only trivial
    ``all_of`` scalar equality checks.
    """

    composed = selector.get("selector", selector)
    all_of = composed.get("all_of", [])

    for clause in all_of:
        graph = clause.get("graph")
        where = clause.get("where", {})
        graph_values = facts.get(graph, {})
        for key, value in where.items():
            if isinstance(value, dict):
                eq_value = value.get("eq", None)
                if eq_value is None:
                    return False
                if graph_values.get(key) != eq_value:
                    return False
            else:
                if graph_values.get(key) != value:
                    return False

    if all_of:
        return True

    # Placeholder: non-all_of composition support to be added.
    return False
