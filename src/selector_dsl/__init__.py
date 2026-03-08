"""Selector DSL package scaffold for Fuzzymodo."""

from .canonical import canonicalize_selector, selector_hash
from .evaluator import evaluate_selector, evaluate_selector_verbose
from .decision_ledger_sqlite import DecisionLedgerRecord
from .exchange import (
    DecisionEgress,
    decision_egress_to_sb_overlay_record,
    evaluate_to_decision_egress,
)
from .replay_artifacts import write_replay_bundle
from .speculation import (
    DecisionRecord,
    SpeculationBranch,
    choose_dominant_branch,
    retire_decision,
)
from .types import ClauseEvaluation, EvaluationResult

__all__ = [
    "canonicalize_selector",
    "selector_hash",
    "evaluate_selector",
    "evaluate_selector_verbose",
    "ClauseEvaluation",
    "EvaluationResult",
    "DecisionEgress",
    "DecisionLedgerRecord",
    "write_replay_bundle",
    "evaluate_to_decision_egress",
    "decision_egress_to_sb_overlay_record",
    "DecisionRecord",
    "SpeculationBranch",
    "choose_dominant_branch",
    "retire_decision",
]
