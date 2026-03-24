from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from selector_dsl.codex_trace import (  # noqa: E402
    codex_trace_decision_to_sb_overlay_record,
    emit_codex_trace_observer_artifacts,
    evaluate_codex_trace,
)


def _selector() -> dict[str, object]:
    return {
        "dsl_version": "0.1",
        "selector": {
            "all_of": [
                {"graph": "execution", "where": {"exec_command_count": {"gte": 1}}},
            ]
        },
    }


def _facts() -> dict[str, object]:
    return {
        "contract_version": "codex_trace_facts_v1",
        "fact_digest": "sha256:facts",
        "graphs": {
            "tool_use": {"exec_command_count": 2},
            "message_flow": {"message_count": 4},
            "outcomes": {
                "completion_candidates": [{"candidate_id": "cand-1"}],
                "open_commitments": [{"external_item_id": "task-1"}],
                "completed_commitments": [],
                "evidence_gaps": [],
                "unresolved_blockers": [],
            },
        },
        "outcomes": {
            "completion_candidates": [{"candidate_id": "cand-1"}],
            "open_commitments": [{"external_item_id": "task-1"}],
            "completed_commitments": [],
            "evidence_gaps": [],
            "unresolved_blockers": [],
        },
        "evidence_refs": [{"ref_kind": "chat_archive_message", "source_id": "codex_1"}],
    }


def test_evaluate_codex_trace_forward_emits_proposals() -> None:
    decision = evaluate_codex_trace(_selector(), facts=_facts(), evaluation_mode="forward_state_build")

    assert decision.decision_egress.matched is True
    kinds = {item["proposal_kind"] for item in decision.proposals}
    assert "completion_candidate" in kinds
    assert "followup_task" in kinds
    assert decision.branch_review_classification is None
    assert decision.evaluation_digest.startswith("sha256:")


def test_evaluate_codex_trace_backward_classifies_supported_miss() -> None:
    decision = evaluate_codex_trace(
        _selector(),
        facts=_facts(),
        evaluation_mode="backward_branch_review",
        outcome_hint={"target_locator": "task-1"},
    )

    assert decision.branch_review_classification == "missed_with_support"
    assert any(item["reason_code"] == "branch_review_classification" for item in decision.reason_codes)


def test_emit_codex_trace_observer_artifacts_smoke() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        overlay = emit_codex_trace_observer_artifacts(
            decision_ledger_db_path=tmp_path / "ledger.sqlite",
            decision_id="dec-trace-1",
            selector_payload=_selector(),
            facts=_facts(),
            activity_event_id="evt-1",
            annotation_id="obs:fuzzymodo:trace:1",
            state_date="2026-03-24",
            provenance={"source": "unit"},
            decision_state="proposed",
            evaluation_mode="backward_branch_review",
            outcome_hint={"target_locator": "task-1"},
            replay_out_root=tmp_path / "runs",
        )

    assert overlay["observer_kind"] == "fuzzymodo_codex_trace_v1"
    assert overlay["selector_refs"][0]["selector_hash"]
    assert any(item["artifact_kind"] == "decision_ledger_ref" for item in overlay["artifact_refs"])
    assert any(item["artifact_kind"] == "codex_trace_proposal" for item in overlay["artifact_refs"])


def test_codex_trace_overlay_record_stays_reference_only() -> None:
    decision = evaluate_codex_trace(_selector(), facts=_facts(), evaluation_mode="forward_state_build")
    overlay = codex_trace_decision_to_sb_overlay_record(
        decision,
        activity_event_id="evt-1",
        annotation_id="obs:fuzzymodo:trace:2",
        state_date="2026-03-24",
        provenance={"source": "unit"},
        decision_state="proposed",
    )

    assert overlay["observer_kind"] == "fuzzymodo_codex_trace_v1"
    assert "selector" not in overlay
    assert "norm_constraints" not in overlay
    assert overlay["canonical_status"] == "derived_only"
    assert "derived_only" in overlay["overlay_flags"]
