"""Type aliases for selector DSL payloads.

This file intentionally keeps aliases simple until the schema-driven parser is
implemented.
"""

from __future__ import annotations

from typing import Any, Dict

SelectorPayload = Dict[str, Any]
ClausePayload = Dict[str, Any]
GraphFacts = Dict[str, Dict[str, Any]]
