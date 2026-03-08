from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from selector_dsl.adapters import emit_fuzzymodo_observer_artifacts  # noqa: E402


def test_emit_fuzzymodo_observer_artifacts_smoke() -> None:
    selector = {
        "dsl_version": "0.1",
        "selector": {
            "all_of": [
                {"graph": "structural", "where": {"function.name": {"eq": "parse"}}}
            ]
        },
    }
    facts = {"structural": {"function.name": "parse"}}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        ledger_db = tmp_path / "ledger.sqlite"
        out_root = tmp_path / "runs"
        overlay = emit_fuzzymodo_observer_artifacts(
            decision_ledger_db_path=ledger_db,
            decision_id="dec-1",
            selector_payload=selector,
            facts=facts,
            activity_event_id="evt-1",
            annotation_id="obs:fuzzymodo:evt-1",
            state_date="2026-03-09",
            provenance={"source": "fuzzymodo", "run_id": "unit"},
            decision_state="buffered",
            replay_out_root=out_root,
            fact_digest="facts:sha256:deadbeef",
        )

        assert overlay["observer_kind"] == "fuzzymodo_selector_v1"
        assert overlay["selector_refs"][0]["selector_hash"]
        assert any(a["artifact_kind"] == "replay_bundle_dir" for a in overlay["artifact_refs"])
