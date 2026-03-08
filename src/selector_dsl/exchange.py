"""Exchange-channel helpers for fuzzymodo.

v0.1 scope: in-process structures only (no CLI, no network).

This module is an adapter surface that turns selector/norm evaluation results into
reference-heavy artifacts suitable for downstream observers (e.g. StatiBaker
overlay rows) without transferring normative authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .canonical import selector_hash
from .evaluator import evaluate_selector_verbose
from .norms import apply_norm_constraints
from .decision_ledger_sqlite import DecisionLedgerRecord, upsert_decision


@dataclass(frozen=True)
class DecisionEgress:
    selector_hash: str
    matched: bool
    matched_clauses: list[dict[str, Any]]
    rejected_clauses: list[dict[str, Any]]
    errors: list[str]
    evaluated_at: str
    norm_annotation: dict[str, Any] | None = None


def evaluate_to_decision_egress(
    selector_payload: Mapping[str, Any],
    *,
    facts: Mapping[str, Mapping[str, Any]],
    norm_constraints: list[Mapping[str, Any]] | None = None,
    evaluated_at: str | None = None,
) -> DecisionEgress:
    """Channel A/B/C -> Channel D.

    Produces a JSON-serializable decision bundle.
    """

    # Hash selectors only (not full payload wrappers).
    composed = selector_payload.get("selector", selector_payload)
    shash = selector_hash(composed)

    res = evaluate_selector_verbose(selector_payload, facts)

    if evaluated_at is None:
        evaluated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    norm_annotation: dict[str, Any] | None = None
    if norm_constraints is not None:
        ann = apply_norm_constraints(norm_constraints, facts=facts)
        norm_annotation = {
            "applied": [
                {
                    "constraint_id": a.constraint_id,
                    "mode": a.mode,
                    "bug_classes": list(a.bug_classes),
                }
                for a in ann.applied
            ],
            "stale_constraints": list(ann.stale_constraints),
            "errors": list(ann.errors),
        }

    return DecisionEgress(
        selector_hash=shash,
        matched=bool(res.matched),
        matched_clauses=[dict(ce.clause) for ce in res.matched_clauses],
        rejected_clauses=[dict(ce.clause) for ce in res.rejected_clauses],
        errors=list(res.errors),
        evaluated_at=evaluated_at,
        norm_annotation=norm_annotation,
    )


def persist_decision_ledger(
    *,
    db_path: str | Any,
    decision_id: str,
    decision: DecisionEgress,
    decision_state: str,
    policy_hash: str | None = None,
    replay_key: str | None = None,
    fact_digest: str | None = None,
    decided_by: str | None = None,
    reason_codes: list[Mapping[str, Any]] | None = None,
    artifacts: list[Mapping[str, Any]] | None = None,
) -> str:
    """Persist a decision record to the Path-2 ledger.

    Returns the decision_id for convenience.
    """

    from pathlib import Path

    rec = DecisionLedgerRecord(
        decision_id=str(decision_id),
        selector_hash=str(decision.selector_hash),
        decision_state=str(decision_state),
        matched=1 if decision.matched else 0,
        policy_hash=str(policy_hash) if policy_hash is not None else None,
        replay_key=str(replay_key) if replay_key is not None else None,
        fact_digest=str(fact_digest) if fact_digest is not None else None,
        created_at=str(decision.evaluated_at),
        decided_by=str(decided_by) if decided_by is not None else None,
    )

    upsert_decision(
        db_path=Path(str(db_path)),
        record=rec,
        reason_codes=reason_codes or [{"reason_code": "eval_error", "detail": e} for e in decision.errors],
        artifacts=artifacts or [],
    )
    return rec.decision_id


def decision_egress_to_sb_overlay_record(
    decision: DecisionEgress,
    *,
    activity_event_id: str,
    annotation_id: str,
    state_date: str,
    provenance: Mapping[str, Any],
    status: str | None = None,
    confidence: str | None = None,
    decision_state: str | None = None,
    policy_hash: str | None = None,
    replay_key: str | None = None,
    artifacts: list[Mapping[str, Any]] | None = None,
    decision_ledger_id: str | None = None,
) -> dict[str, Any]:
    """Channel D -> Channel F.

    Emit a reference-heavy StatiBaker overlay record for observer_kind
    "fuzzymodo_selector_v1".

    Important: this does NOT include selector or norm payloads.
    """

    selector_refs = [
        {
            "selector_hash": decision.selector_hash,
            "decision_state": decision_state,
            "matched": 1 if decision.matched else 0,
            "policy_hash": policy_hash,
            "replay_key": replay_key,
            "created_at": decision.evaluated_at,
        }
    ]

    reason_codes: list[dict[str, Any]] = []
    for err in decision.errors:
        reason_codes.append({"reason_code": "eval_error", "detail": str(err)})

    artifact_refs: list[dict[str, Any]] = []
    if decision_ledger_id:
        artifact_refs.append(
            {
                "artifact_kind": "decision_ledger_ref",
                "artifact_locator": f"fuzzymodo_decision_ledger:{decision_ledger_id}",
                "artifact_hash": None,
            }
        )

    for a in artifacts or []:
        if not isinstance(a, Mapping):
            continue
        artifact_refs.append(
            {
                "artifact_kind": str(a.get("artifact_kind") or ""),
                "artifact_locator": str(a.get("artifact_locator") or ""),
                "artifact_hash": a.get("artifact_hash"),
            }
        )

    return {
        "activity_event_id": str(activity_event_id),
        "annotation_id": str(annotation_id),
        "provenance": dict(provenance),
        "state_date": str(state_date),
        "observer_kind": "fuzzymodo_selector_v1",
        "status": status,
        "confidence": confidence,
        "selector_refs": selector_refs,
        "reason_codes": reason_codes,
        "artifact_refs": artifact_refs,
    }
