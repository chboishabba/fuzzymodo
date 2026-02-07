"""Selector DSL package scaffold for Fuzzymodo."""

from .canonical import canonicalize_selector, selector_hash
from .evaluator import evaluate_selector

__all__ = [
    "canonicalize_selector",
    "selector_hash",
    "evaluate_selector",
]
