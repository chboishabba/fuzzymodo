"""Selector DSL package scaffold for Fuzzymodo."""

from .canonical import canonicalize_selector, selector_hash
from .evaluator import evaluate_selector, evaluate_selector_verbose
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
    "evaluate_selector_verbose",
    "ClauseEvaluation",
    "EvaluationResult",
    "DecisionRecord",
    "SpeculationBranch",
    "choose_dominant_branch",
    "retire_decision",
]
