"""StatiBaker overlay emitter for fuzzymodo selector outcomes.

This emits reference-only overlay records suitable for ingestion via:
`StatiBaker/sb/itir_ingest.persist_overlays()`.

Contract: docs/planning/fuzzymodo_statiBaker_interface_20260309.md
Boundary: do NOT include raw selector DSL payloads or norm constraints.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from .canonical import selector_hash
from .types import EvaluationResult


@dataclass(frozen=True)
class SBArtifactRef:
    artifact_kind: str
    artifact_locator: str
    artifact_hash: str | None = None


@dataclass(frozen=True)
class SBReasonCode:
    reason_code: str
    detail: str | None = None


def emit_sb_fuzzymodo_selector_overlay(
    *,
    activity_event_id: str,
    annotation_id: str,
    state_date: str | None = None,
    sb_state_id: str | None = None,
    provenance: Mapping[str, Any] | None = None,
    selector: Mapping[str, Any],
    result: EvaluationResult,
    decision_state: str | None = None,
    policy_hash: str | None = None,
    replay_key: str | None = None,
    artifacts: Sequence[SBArtifactRef] | None = None,
    reason_codes: Sequence[SBReasonCode] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    if not activity_event_id:
        raise ValueError("activity_event_id is required")
    if not annotation_id:
        raise ValueError("annotation_id is required")
    if state_date is None and sb_state_id is None:
        raise ValueError("state_date or sb_state_id is required")

    sel_hash = selector_hash(selector)

    record: dict[str, Any] = {
        "activity_event_id": activity_event_id,
        "annotation_id": annotation_id,
        "observer_kind": "fuzzymodo_selector_v1",
        "provenance": dict(provenance or {}),
    }
    if state_date is not None:
        record["state_date"] = state_date
    if sb_state_id is not None:
        record["sb_state_id"] = sb_state_id

    record["selector_refs"] = [
        {
            "selector_hash": sel_hash,
            "decision_state": decision_state,
            "matched": 1 if result.matched else 0,
            "policy_hash": policy_hash,
            "replay_key": replay_key,
            "created_at": created_at,
        }
    ]

    if reason_codes:
        record["reason_codes"] = [asdict(x) for x in reason_codes]
    else:
        record["reason_codes"] = []

    if artifacts:
        record["artifact_refs"] = [asdict(x) for x in artifacts]
    else:
        record["artifact_refs"] = []

    return record
