"""Selector DSL validation.

We validate two things:
1) Basic structure (schema-ish) so the evaluator behaves deterministically.
2) Semantic constraints that are easier to express in code (e.g. non-empty lists,
   allowed operators, regex compilation).

We intentionally avoid adding dependencies for v0.1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


_ALLOWED_GRAPHS = {
    "structural",
    "execution",
    "build",
    "threat",
    "ecosystem",
    "normative",
    "timeline",
}

_ALLOWED_OPERATORS = {
    "eq",
    "neq",
    "lt",
    "lte",
    "gt",
    "gte",
    "in",
    "startswith",
    "matches",
    "exists",
}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _validate_predicate(predicate: Any, *, path: str, errors: list[str]) -> None:
    if _is_scalar(predicate):
        return

    if not isinstance(predicate, Mapping):
        errors.append(f"{path}: predicate must be scalar or object")
        return

    if not predicate:
        errors.append(f"{path}: predicate object must have at least one operator")
        return

    for op, expected in predicate.items():
        if op not in _ALLOWED_OPERATORS:
            errors.append(f"{path}: invalid operator '{op}'")
            continue

        if op in {"lt", "lte", "gt", "gte"}:
            if not isinstance(expected, (int, float)) or isinstance(expected, bool):
                errors.append(f"{path}.{op}: expected number")
        elif op == "in":
            if not isinstance(expected, Sequence) or isinstance(expected, (str, bytes)):
                errors.append(f"{path}.in: expected non-empty array")
            elif len(expected) == 0:
                errors.append(f"{path}.in: expected non-empty array")
            else:
                for i, item in enumerate(expected):
                    if not _is_scalar(item):
                        errors.append(f"{path}.in[{i}]: expected scalar")
        elif op == "startswith":
            if not isinstance(expected, str):
                errors.append(f"{path}.startswith: expected string")
        elif op == "matches":
            if not isinstance(expected, str):
                errors.append(f"{path}.matches: expected string")
            else:
                try:
                    re.compile(expected)
                except re.error as e:
                    errors.append(f"{path}.matches: invalid regex ({e})")
        elif op == "exists":
            if not isinstance(expected, bool):
                errors.append(f"{path}.exists: expected boolean")
        else:
            # eq/neq accept scalars
            if not _is_scalar(expected):
                errors.append(f"{path}.{op}: expected scalar")


def _validate_clause(clause: Any, *, path: str, errors: list[str]) -> None:
    if not isinstance(clause, Mapping):
        errors.append(f"{path}: clause must be object")
        return

    graph = clause.get("graph")
    if graph not in _ALLOWED_GRAPHS:
        errors.append(f"{path}.graph: invalid graph")

    where = clause.get("where")
    if not isinstance(where, Mapping):
        errors.append(f"{path}.where: where must be object")
        return
    if not where:
        errors.append(f"{path}.where: must have at least one predicate")
        return

    for field, predicate in where.items():
        if not isinstance(field, str) or not field:
            errors.append(f"{path}.where: field keys must be non-empty strings")
            continue
        _validate_predicate(predicate, path=f"{path}.where.{field}", errors=errors)


def validate_selector_payload(payload: Any) -> ValidationResult:
    """Validate either a full selector payload or a raw selector object.

    Accepted shapes:
    - {"dsl_version": "0.1", "selector": {...}}
    - {...}  (treated as selector object)
    """

    errors: list[str] = []

    if not isinstance(payload, Mapping):
        return ValidationResult(ok=False, errors=["payload: must be object"])

    selector_obj: Any
    if "selector" in payload and "dsl_version" in payload:
        dsl_version = payload.get("dsl_version")
        if not isinstance(dsl_version, str) or not dsl_version:
            errors.append("dsl_version: must be non-empty string")
        selector_obj = payload.get("selector")
    elif "selector" in payload:
        # Back-compat: allow payloads without dsl_version.
        selector_obj = payload.get("selector")
    else:
        selector_obj = payload

    if not isinstance(selector_obj, Mapping):
        errors.append("selector: must be object")
        return ValidationResult(ok=False, errors=errors)

    all_of = selector_obj.get("all_of")
    any_of = selector_obj.get("any_of")
    not_clause = selector_obj.get("not")

    if all_of is None and any_of is None and not_clause is None:
        errors.append("selector: must include at least one of all_of/any_of/not")
        return ValidationResult(ok=False, errors=errors)

    if all_of is not None:
        if not isinstance(all_of, list) or not all_of:
            errors.append("selector.all_of: must be non-empty array")
        else:
            for i, clause in enumerate(all_of):
                _validate_clause(clause, path=f"selector.all_of[{i}]", errors=errors)

    if any_of is not None:
        if not isinstance(any_of, list) or not any_of:
            errors.append("selector.any_of: must be non-empty array")
        else:
            for i, clause in enumerate(any_of):
                _validate_clause(clause, path=f"selector.any_of[{i}]", errors=errors)

    if not_clause is not None:
        _validate_clause(not_clause, path="selector.not", errors=errors)

    return ValidationResult(ok=(len(errors) == 0), errors=errors)
