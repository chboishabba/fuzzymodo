"""Selector DSL package scaffold for Fuzzymodo."""

from .canonical import canonicalize_selector, selector_hash
from .evaluator import evaluate_selector
from .speculation import (
    DecisionRecord,
    SpeculationBranch,
    choose_dominant_branch,
    retire_decision,
)

__all__ = [
    "canonicalize_selector",
    "selector_hash",
    "evaluate_selector",
    "DecisionRecord",
    "SpeculationBranch",
    "choose_dominant_branch",
    "retire_decision",
]
