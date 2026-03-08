"""Convenience adapters (glue).

These are single-call helpers that combine evaluation, replay artifact emission,
decision ledger upsert, and SB overlay record emission.

They remain library-only and do not perform any SB DB writes.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from .decision_ledger_sqlite import DecisionLedgerRecord, upsert_decision
from .exchange import (
    DecisionEgress,
    decision_egress_to_sb_overlay_record,
    evaluate_to_decision_egress,
)
from .replay_artifacts import write_replay_bundle


def emit_fuzzymodo_observer_artifacts(
    *,
    decision_ledger_db_path: Path,
    decision_id: str,
    selector_payload: Mapping[str, Any],
    facts: Mapping[str, Mapping[str, Any]],
    activity_event_id: str,
    annotation_id: str,
    state_date: str,
    provenance: Mapping[str, Any],
    decision_state: str,
    fact_digest: str | None = None,
    policy_hash: str | None = None,
    replay_key: str | None = None,
    replay_out_root: Path | None = None,
) -> dict[str, Any]:
    """Produce a decision ledger row + replay bundle + SB overlay record.

    Returns the SB overlay record dict (reference-only).
    """

    decision: DecisionEgress = evaluate_to_decision_egress(selector_payload, facts=facts)

    # Write replay artifacts and include a locator the SB overlay can reference.
    replay_dir = write_replay_bundle(
        decision,
        selector_payload=selector_payload,
        out_root=replay_out_root,
        fact_digest=fact_digest,
    )

    # Upsert decision ledger.
    rec = DecisionLedgerRecord(
        decision_id=decision_id,
        selector_hash=decision.selector_hash,
        decision_state=decision_state,
        matched=1 if decision.matched else 0,
        policy_hash=policy_hash,
        replay_key=replay_key,
        fact_digest=fact_digest,
        created_at=decision.evaluated_at,
        decided_by=None,
    )

    upsert_decision(
        db_path=decision_ledger_db_path,
        record=rec,
        reason_codes=[{"reason_code": "eval_error", "detail": e} for e in decision.errors],
        artifacts=[
            {
                "artifact_kind": "replay_bundle_dir",
                "artifact_locator": str(replay_dir),
                "artifact_hash": None,
            }
        ],
    )

    overlay = decision_egress_to_sb_overlay_record(
        decision,
        activity_event_id=activity_event_id,
        annotation_id=annotation_id,
        state_date=state_date,
        provenance=provenance,
        decision_state=decision_state,
        policy_hash=policy_hash,
        replay_key=replay_key,
        decision_ledger_id=decision_id,
        artifacts=[
            {
                "artifact_kind": "replay_bundle_dir",
                "artifact_locator": str(replay_dir),
                "artifact_hash": None,
            }
        ],
    )

    return overlay
