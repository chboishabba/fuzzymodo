from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from selector_dsl.exchange import (  # noqa: E402
    decision_egress_to_sb_overlay_record,
    evaluate_to_decision_egress,
)


def test_channel_d_decision_egress_shape() -> None:
    selector = {
        "dsl_version": "0.1",
        "selector": {
            "all_of": [
                {"graph": "structural", "where": {"function.name": {"eq": "parse"}}}
            ]
        },
    }
    facts = {"structural": {"function.name": "parse"}}
    d = evaluate_to_decision_egress(selector, facts=facts)
    assert d.selector_hash
    assert d.matched is True
    assert isinstance(d.matched_clauses, list)
    assert isinstance(d.rejected_clauses, list)
    assert isinstance(d.errors, list)
    assert d.evaluated_at.endswith("Z")


def test_channel_f_sb_overlay_record_is_reference_only() -> None:
    selector = {
        "dsl_version": "0.1",
        "selector": {
            "all_of": [
                {"graph": "structural", "where": {"function.name": {"eq": "parse"}}}
            ]
        },
    }
    facts = {"structural": {"function.name": "parse"}}
    d = evaluate_to_decision_egress(selector, facts=facts)

    overlay = decision_egress_to_sb_overlay_record(
        d,
        activity_event_id="evt-1",
        annotation_id="obs:fuzzymodo:evt-1",
        state_date="2026-03-09",
        provenance={"source": "fuzzymodo", "run_id": "unit"},
        decision_state="buffered",
        replay_key="replay:abc",
        artifacts=[
            {
                "artifact_kind": "replay_artifact",
                "artifact_locator": "artifacts/fuzzymodo/runs/x/replay.json",
                "artifact_hash": "a" * 64,
            }
        ],
    )

    assert overlay["observer_kind"] == "fuzzymodo_selector_v1"
    assert "selector" not in overlay
    assert "norm_constraints" not in overlay
    assert overlay["selector_refs"][0]["selector_hash"] == d.selector_hash
    assert overlay["artifact_refs"][0]["artifact_kind"] == "replay_artifact"
