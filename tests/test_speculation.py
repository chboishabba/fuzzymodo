from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from selector_dsl.speculation import (  # noqa: E402
    DecisionRecord,
    SpeculationBranch,
    choose_dominant_branch,
    retire_decision,
)


def test_choose_dominant_branch_by_score_then_cost() -> None:
    selected = choose_dominant_branch(
        [
            SpeculationBranch(branch_id="b-low", score=0.4, rollback_cost=1.0),
            SpeculationBranch(branch_id="b-hi-cost", score=0.9, rollback_cost=2.0),
            SpeculationBranch(branch_id="b-hi-low", score=0.9, rollback_cost=0.5),
        ]
    )
    assert selected.branch_id == "b-hi-low"


def test_retire_buffered_decision() -> None:
    record = DecisionRecord(branch_id="b1", state="buffered")
    approved = retire_decision(record, approve=True)
    rejected = retire_decision(record, approve=False)
    assert approved.state == "approved"
    assert rejected.state == "rejected"


def test_retire_requires_buffered_state() -> None:
    with pytest.raises(ValueError):
        retire_decision(DecisionRecord(branch_id="b1", state="running"), approve=True)

