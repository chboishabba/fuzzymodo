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

    Raises ``TypeError`` if the object cannot be serialized.
    """

    return json.dumps(selector, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def selector_hash(selector: Any) -> str:
    """Return lowercase hex SHA-256 of canonical selector JSON."""

    canonical = canonicalize_selector(selector)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
