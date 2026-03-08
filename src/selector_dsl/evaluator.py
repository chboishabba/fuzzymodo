"""Selector evaluator implementing all_of / any_of / not semantics."""

from __future__ import annotations

import re
from typing import Any, Mapping

from .types import ClauseEvaluation, EvaluationResult
from .validation import validate_selector_payload


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _eval_operator(
    actual: Any,
    operator: str,
    expected: Any,
    field_exists: bool,
    *,
    errors: list[str] | None = None,
    path: str = "",
) -> bool:
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
        try:
            return actual in expected
        except TypeError:
            return False
    if operator == "startswith":
        return isinstance(actual, str) and actual.startswith(expected)
    if operator == "matches":
        if not isinstance(actual, str):
            return False
        try:
            return re.search(expected, actual) is not None
        except re.error as e:
            if errors is not None:
                suffix = f" ({path})" if path else ""
                errors.append(f"invalid regex: {e}{suffix}")
            return False
    if operator == "exists":
        return field_exists is bool(expected)
    return False


def _eval_predicate(
    actual: Any,
    predicate: Any,
    field_exists: bool,
    *,
    errors: list[str] | None = None,
    path: str = "",
) -> bool:
    if isinstance(predicate, dict):
        for op, expected in predicate.items():
            if not _eval_operator(
                actual,
                op,
                expected,
                field_exists,
                errors=errors,
                path=f"{path}.{op}" if path else op,
            ):
                return False
        return True
    return actual == predicate


def _eval_clause(
    clause: Mapping[str, Any],
    facts: Mapping[str, Mapping[str, Any]],
    *,
    errors: list[str] | None = None,
    path: str = "",
) -> bool:
    graph = clause.get("graph")
    where = clause.get("where", {})
    graph_values = facts.get(graph, {})
    if not isinstance(where, dict):
        return False
    for key, predicate in where.items():
        exists = key in graph_values
        actual = graph_values.get(key)
        if not _eval_predicate(
            actual,
            predicate,
            exists,
            errors=errors,
            path=f"{path}.{graph}.{key}" if path else f"{graph}.{key}",
        ):
            return False
    return True


def evaluate_selector_verbose(
    selector: Mapping[str, Any], facts: Mapping[str, Mapping[str, Any]]
) -> EvaluationResult:
    """Evaluate selector and return a structured result.

    This performs validation first; invalid payloads yield matched=False with
    errors populated and empty clause lists.
    """

    validation = validate_selector_payload(selector)
    if not validation.ok:
        return EvaluationResult(
            matched=False,
            errors=validation.errors,
            matched_clauses=[],
            rejected_clauses=[],
        )

    errors: list[str] = []

    composed = selector.get("selector", selector)

    matched_clauses: list[ClauseEvaluation] = []
    rejected_clauses: list[ClauseEvaluation] = []

    def _record_clause(clause: Mapping[str, Any]) -> bool:
        ok = _eval_clause(clause, facts, errors=errors, path="where")
        ce = ClauseEvaluation(clause=dict(clause), matched=ok)
        if ok:
            matched_clauses.append(ce)
        else:
            rejected_clauses.append(ce)
        return ok

    all_of = composed.get("all_of")
    any_of = composed.get("any_of")
    not_clause = composed.get("not")

    ok = True

    if all_of is not None:
        ok = ok and all(_record_clause(clause) for clause in all_of)

    if any_of is not None:
        # Any-of is true if at least one clause matched.
        any_ok = False
        for clause in any_of:
            if _record_clause(clause):
                any_ok = True
        ok = ok and any_ok

    if not_clause is not None:
        not_ok = not _record_clause(not_clause)
        ok = ok and not_ok

    return EvaluationResult(
        matched=ok,
        errors=errors,
        matched_clauses=matched_clauses,
        rejected_clauses=rejected_clauses,
    )


def evaluate_selector(selector: Mapping[str, Any], facts: Mapping[str, Mapping[str, Any]]) -> bool:
    """Evaluate selector against graph-scoped facts."""

    return evaluate_selector_verbose(selector, facts).matched

