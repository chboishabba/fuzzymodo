"""Speculation branch and normative-retirement helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SpeculationBranch:
    """A candidate branch explored before normative commitment."""

    branch_id: str
    score: float
    rollback_cost: float


@dataclass(frozen=True)
class DecisionRecord:
    """Normative retirement state for a completed branch."""

    branch_id: str
    state: str

    def validate(self) -> None:
        if self.state not in {"proposed", "running", "buffered", "approved", "rejected"}:
            raise ValueError(f"Invalid decision state: {self.state}")


def choose_dominant_branch(branches: Iterable[SpeculationBranch]) -> SpeculationBranch:
    """Select highest score branch, then lowest rollback cost, then id."""

    items = list(branches)
    if not items:
        raise ValueError("At least one branch is required")
    return sorted(items, key=lambda b: (-b.score, b.rollback_cost, b.branch_id))[0]


def retire_decision(record: DecisionRecord, *, approve: bool) -> DecisionRecord:
    """Transition buffered branch to a terminal approval decision."""

    record.validate()
    if record.state != "buffered":
        raise ValueError("Only buffered decisions can be retired")
    return DecisionRecord(branch_id=record.branch_id, state="approved" if approve else "rejected")

