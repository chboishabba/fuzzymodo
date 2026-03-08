"""Type aliases for selector DSL payloads.

This file intentionally keeps aliases simple until the schema-driven parser is
implemented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

SelectorPayload = Dict[str, Any]
ClausePayload = Dict[str, Any]
GraphFacts = Dict[str, Dict[str, Any]]


@dataclass(frozen=True)
class ClauseEvaluation:
    clause: Mapping[str, Any]
    matched: bool
    reason: Optional[str] = None


@dataclass(frozen=True)
class EvaluationResult:
    matched: bool
    errors: List[str]
    matched_clauses: List[ClauseEvaluation]
    rejected_clauses: List[ClauseEvaluation]
