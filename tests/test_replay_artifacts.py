from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from selector_dsl.exchange import evaluate_to_decision_egress  # noqa: E402
from selector_dsl.replay_artifacts import write_replay_bundle  # noqa: E402


def test_write_replay_bundle_writes_expected_files() -> None:
    selector = {
        "dsl_version": "0.1",
        "selector": {
            "all_of": [
                {"graph": "structural", "where": {"function.name": {"eq": "parse"}}}
            ]
        },
    }
    facts = {"structural": {"function.name": "parse"}}

    decision = evaluate_to_decision_egress(selector, facts=facts, evaluated_at="2026-03-09T00:00:00Z")

    with tempfile.TemporaryDirectory() as tmp:
        out_root = Path(tmp) / "runs"
        out_dir = write_replay_bundle(
            decision,
            selector_payload=selector,
            out_root=out_root,
            fact_digest="facts:sha256:deadbeef",
        )

        assert (out_dir / "selector.json").exists()
        assert (out_dir / "decision.json").exists()
        assert (out_dir / "meta.json").exists()

        meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
        assert meta["selector_hash"] == decision.selector_hash
        assert meta["fact_digest"] == "facts:sha256:deadbeef"
