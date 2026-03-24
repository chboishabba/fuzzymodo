"""Selector DSL package scaffold for Fuzzymodo."""

from .canonical import canonicalize_selector, selector_hash
from .evaluator import evaluate_selector, evaluate_selector_verbose
from .decision_ledger_sqlite import DecisionLedgerRecord
from .exchange import (
    DecisionEgress,
    decision_egress_to_sb_overlay_record,
    evaluate_to_decision_egress,
)
from .casey_adapter import evaluate_casey_export
from .adapters import emit_fuzzymodo_observer_artifacts
from .codex_trace import (
    CodexTraceDecision,
    codex_trace_decision_to_sb_overlay_record,
    emit_codex_trace_observer_artifacts,
    evaluate_codex_trace,
    selector_graph_facts_from_codex_trace,
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
    "emit_fuzzymodo_observer_artifacts",
    "emit_codex_trace_observer_artifacts",
    "write_replay_bundle",
    "evaluate_to_decision_egress",
    "decision_egress_to_sb_overlay_record",
    "CodexTraceDecision",
    "evaluate_codex_trace",
    "selector_graph_facts_from_codex_trace",
    "codex_trace_decision_to_sb_overlay_record",
    "evaluate_casey_export",
    "DecisionRecord",
    "SpeculationBranch",
    "choose_dominant_branch",
    "retire_decision",
]
