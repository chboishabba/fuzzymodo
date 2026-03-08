"""Norm-constraint helpers.

Norms are managed by ITIR. Fuzzymodo only supports:
- validating/parsing norm-constraint payloads
- determining staleness (selector no longer matches facts)
- annotating evaluation output with constraint effects
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .evaluator import evaluate_selector_verbose
from .validation import validate_selector_payload


_ALLOWED_EFFECT_MODES = {"prune", "downgrade", "escalate"}


@dataclass(frozen=True)
class NormApplication:
    constraint_id: str
    mode: str
    bug_classes: list[str]


@dataclass(frozen=True)
class NormsAnnotation:
    applied: list[NormApplication]
    stale_constraints: list[str]
    errors: list[str]


def validate_norm_constraint(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return ["norm_constraint: must be object"]

    for key in ("id", "dsl_version", "selector", "assertion", "effect", "provenance"):
        if key not in payload:
            errors.append(f"norm_constraint.{key}: required")

    cid = payload.get("id")
    if cid is not None and (not isinstance(cid, str) or not cid):
        errors.append("norm_constraint.id: must be non-empty string")

    dsl_version = payload.get("dsl_version")
    if dsl_version is not None and (not isinstance(dsl_version, str) or not dsl_version):
        errors.append("norm_constraint.dsl_version: must be non-empty string")

    selector = payload.get("selector")
    if selector is not None:
        sel = validate_selector_payload({"dsl_version": "0.1", "selector": selector})
        if not sel.ok:
            errors.extend([f"norm_constraint.selector: {e}" for e in sel.errors])

    effect = payload.get("effect")
    if effect is not None:
        if not isinstance(effect, Mapping):
            errors.append("norm_constraint.effect: must be object")
        else:
            mode = effect.get("mode")
            if mode not in _ALLOWED_EFFECT_MODES:
                errors.append("norm_constraint.effect.mode: invalid")
            bug_classes = effect.get("bug_classes")
            if not isinstance(bug_classes, list) or not bug_classes or not all(
                isinstance(x, str) and x for x in bug_classes
            ):
                errors.append("norm_constraint.effect.bug_classes: must be non-empty string array")

    return errors


def apply_norm_constraints(
    norm_constraints: Iterable[Mapping[str, Any]],
    *,
    facts: Mapping[str, Mapping[str, Any]],
) -> NormsAnnotation:
    applied: list[NormApplication] = []
    stale: list[str] = []
    errors: list[str] = []

    for nc in norm_constraints:
        nc_errors = validate_norm_constraint(nc)
        if nc_errors:
            errors.extend(nc_errors)
            continue

        cid = str(nc["id"])
        selector = nc["selector"]

        # Stale if selector does not match current facts.
        result = evaluate_selector_verbose({"dsl_version": "0.1", "selector": selector}, facts)
        if not result.matched:
            stale.append(cid)
            continue

        eff = nc["effect"]
        applied.append(
            NormApplication(
                constraint_id=cid,
                mode=str(eff["mode"]),
                bug_classes=[str(x) for x in eff.get("bug_classes", [])],
            )
        )

    return NormsAnnotation(applied=applied, stale_constraints=stale, errors=errors)
