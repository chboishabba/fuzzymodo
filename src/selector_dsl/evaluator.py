"""Selector evaluator implementing all_of / any_of / not semantics."""

from __future__ import annotations

import re
from typing import Any, Mapping


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _eval_operator(actual: Any, operator: str, expected: Any, field_exists: bool) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected
    if operator == "lt":
        return _is_number(actual) and actual < expected
    if operator == "lte":
        return _is_number(actual) and actual <= expected
    if operator == "gt":
        return _is_number(actual) and actual > expected
    if operator == "gte":
        return _is_number(actual) and actual >= expected
    if operator == "in":
        return actual in expected
    if operator == "startswith":
        return isinstance(actual, str) and actual.startswith(expected)
    if operator == "matches":
        if not isinstance(actual, str):
            return False
        try:
            return re.search(expected, actual) is not None
        except re.error:
            return False
    if operator == "exists":
        return field_exists is bool(expected)
    return False


def _eval_predicate(actual: Any, predicate: Any, field_exists: bool) -> bool:
    if isinstance(predicate, dict):
        for op, expected in predicate.items():
            if not _eval_operator(actual, op, expected, field_exists):
                return False
        return True
    return actual == predicate


def _eval_clause(clause: Mapping[str, Any], facts: Mapping[str, Mapping[str, Any]]) -> bool:
    graph = clause.get("graph")
    where = clause.get("where", {})
    graph_values = facts.get(graph, {})
    if not isinstance(where, dict):
        return False
    for key, predicate in where.items():
        exists = key in graph_values
        actual = graph_values.get(key)
        if not _eval_predicate(actual, predicate, exists):
            return False
    return True


def evaluate_selector(selector: Mapping[str, Any], facts: Mapping[str, Mapping[str, Any]]) -> bool:
    """Evaluate selector against graph-scoped facts.

    Supported composition semantics:
    - ``all_of``: all clauses must pass
    - ``any_of``: at least one clause must pass
    - ``not``: clause must fail
    """

    composed = selector.get("selector", selector)
    if not isinstance(composed, Mapping):
        return False

    all_of = composed.get("all_of")
    any_of = composed.get("any_of")
    not_clause = composed.get("not")

    if all_of is None and any_of is None and not_clause is None:
        return False

    if all_of is not None:
        if not isinstance(all_of, list) or not all_of:
            return False
        if not all(_eval_clause(clause, facts) for clause in all_of):
            return False

    if any_of is not None:
        if not isinstance(any_of, list) or not any_of:
            return False
        if not any(_eval_clause(clause, facts) for clause in any_of):
            return False

    if not_clause is not None:
        if not isinstance(not_clause, Mapping):
            return False
        if _eval_clause(not_clause, facts):
            return False

    return True

