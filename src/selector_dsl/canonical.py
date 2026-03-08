"""Canonicalization helpers for selector payloads.

This first pass intentionally stays minimal: it normalizes key ordering via
JSON canonical serialization and exposes deterministic SHA-256 hashing.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonicalize_selector(selector: Any) -> str:
    """Return canonical JSON for a selector object.

    v0.1 canonicalization rules (selectors only):
    - JSON with sorted keys
    - separators (',', ':')
    - ensure_ascii=True

    Array order is preserved.

    Raises ``TypeError`` if the object cannot be serialized.
    """

    return json.dumps(selector, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _normalize_newlines_in_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return obj.replace("\r\n", "\n").replace("\r", "\n")
    if isinstance(obj, list):
        return [_normalize_newlines_in_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _normalize_newlines_in_obj(v) for k, v in obj.items()}
    return obj


def selector_hash(selector: Any) -> str:
    """Return lowercase hex SHA-256 of canonical selector JSON.

    Hash input is the canonical JSON string with CRLF/CR normalized to LF.
    """

    normalized = _normalize_newlines_in_obj(selector)
    canonical = canonicalize_selector(normalized)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
