from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from selector_dsl.decision_ledger_sqlite import (  # noqa: E402
    DecisionLedgerRecord,
    load_decision,
    upsert_decision,
)


def test_decision_ledger_roundtrip() -> None:
    rec = DecisionLedgerRecord(
        decision_id="dec-1",
        selector_hash="a" * 64,
        decision_state="buffered",
        matched=1,
        policy_hash=None,
        replay_key="replay:abc",
        fact_digest="facts:sha256:deadbeef",
        created_at="2026-03-09T00:00:00Z",
        decided_by=None,
    )

    reasons = [{"reason_code": "policy_gate", "detail": "requires_human"}]
    artifacts = [
        {
            "artifact_kind": "replay_artifact",
            "artifact_locator": "artifacts/fuzzymodo/runs/x/replay.json",
            "artifact_hash": "b" * 64,
        }
    ]

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "fuzzymodo_decisions.sqlite"
        upsert_decision(db_path=db_path, record=rec, reason_codes=reasons, artifacts=artifacts)
        loaded = load_decision(db_path=db_path, decision_id="dec-1")

    assert loaded is not None
    assert loaded["decision_id"] == "dec-1"
    assert loaded["selector_hash"] == "a" * 64
    assert loaded["reason_codes"][0]["reason_code"] == "policy_gate"
    assert loaded["artifacts"][0]["artifact_kind"] == "replay_artifact"
