"""Replay artifact writer (Channel E).

Writes a diff-friendly bundle of files for deterministic replay.

v0.1 contract (bundle):
- selector.json (canonical selector object JSON)
- decision.json (DecisionEgress JSON)
- meta.json (light metadata + optional fact_digest)

Artifacts live under fuzzymodo/artifacts/fuzzymodo/runs/<timestamp>/ by default.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .canonical import canonicalize_selector
from .exchange import DecisionEgress


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_replay_bundle(
    decision: DecisionEgress,
    *,
    selector_payload: Mapping[str, Any],
    out_root: Path | None = None,
    fact_digest: str | None = None,
) -> Path:
    """Write a replay bundle directory and return its path."""

    composed = selector_payload.get("selector", selector_payload)

    if out_root is None:
        out_root = Path(__file__).resolve().parents[3] / "artifacts" / "fuzzymodo" / "runs"

    out_dir = out_root / _now_stamp()
    out_dir.mkdir(parents=True, exist_ok=False)

    (out_dir / "selector.json").write_text(canonicalize_selector(composed) + "\n", encoding="utf-8")

    # DecisionEgress is already JSON-serializable by construction.
    (out_dir / "decision.json").write_text(
        json.dumps(asdict(decision), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    meta = {
        "dsl_version": str(selector_payload.get("dsl_version") or ""),
        "selector_hash": decision.selector_hash,
        "evaluated_at": decision.evaluated_at,
        "fact_digest": fact_digest,
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    return out_dir
