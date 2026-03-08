"""SQLite decision ledger for fuzzymodo.

This is an observer ledger that downstream systems (e.g. StatiBaker) may reference
by id/hash/locator, but must not ingest as canonical SB state.

v0.1: DB-backed, reference-heavy, deterministic fields.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class DecisionLedgerRecord:
    decision_id: str
    selector_hash: str
    decision_state: str
    matched: int | None
    policy_hash: str | None
    replay_key: str | None
    fact_digest: str | None
    created_at: str
    decided_by: str | None
    source_tool: str = "fuzzymodo"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA journal_mode=DELETE;")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS fuzzymodo_decision_ledger (
          decision_id TEXT PRIMARY KEY,
          selector_hash TEXT NOT NULL,
          decision_state TEXT NOT NULL,
          matched INTEGER,
          policy_hash TEXT,
          replay_key TEXT,
          fact_digest TEXT,
          created_at TEXT NOT NULL,
          decided_by TEXT,
          source_tool TEXT NOT NULL DEFAULT 'fuzzymodo'
        );

        CREATE TABLE IF NOT EXISTS fuzzymodo_decision_ledger_reason_codes (
          decision_id TEXT NOT NULL REFERENCES fuzzymodo_decision_ledger(decision_id) ON DELETE CASCADE,
          ref_order INTEGER NOT NULL,
          reason_code TEXT NOT NULL,
          detail TEXT,
          PRIMARY KEY (decision_id, ref_order)
        );

        CREATE TABLE IF NOT EXISTS fuzzymodo_decision_ledger_artifacts (
          decision_id TEXT NOT NULL REFERENCES fuzzymodo_decision_ledger(decision_id) ON DELETE CASCADE,
          ref_order INTEGER NOT NULL,
          artifact_kind TEXT NOT NULL,
          artifact_locator TEXT NOT NULL,
          artifact_hash TEXT,
          PRIMARY KEY (decision_id, ref_order)
        );
        """
    )


def upsert_decision(
    *,
    db_path: Path,
    record: DecisionLedgerRecord,
    reason_codes: Iterable[Mapping[str, Any]] = (),
    artifacts: Iterable[Mapping[str, Any]] = (),
) -> None:
    with _connect(db_path) as conn:
        ensure_schema(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO fuzzymodo_decision_ledger(
              decision_id, selector_hash, decision_state, matched, policy_hash,
              replay_key, fact_digest, created_at, decided_by, source_tool
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                record.decision_id,
                record.selector_hash,
                record.decision_state,
                record.matched,
                record.policy_hash,
                record.replay_key,
                record.fact_digest,
                record.created_at,
                record.decided_by,
                record.source_tool,
            ),
        )

        conn.execute(
            "DELETE FROM fuzzymodo_decision_ledger_reason_codes WHERE decision_id = ?",
            (record.decision_id,),
        )
        conn.execute(
            "DELETE FROM fuzzymodo_decision_ledger_artifacts WHERE decision_id = ?",
            (record.decision_id,),
        )

        for ref_order, payload in enumerate(reason_codes):
            if not isinstance(payload, Mapping):
                continue
            conn.execute(
                """
                INSERT INTO fuzzymodo_decision_ledger_reason_codes(
                  decision_id, ref_order, reason_code, detail
                ) VALUES (?,?,?,?)
                """,
                (
                    record.decision_id,
                    ref_order,
                    str(payload.get("reason_code") or ""),
                    str(payload.get("detail") or "") if payload.get("detail") is not None else None,
                ),
            )

        for ref_order, payload in enumerate(artifacts):
            if not isinstance(payload, Mapping):
                continue
            conn.execute(
                """
                INSERT INTO fuzzymodo_decision_ledger_artifacts(
                  decision_id, ref_order, artifact_kind, artifact_locator, artifact_hash
                ) VALUES (?,?,?,?,?)
                """,
                (
                    record.decision_id,
                    ref_order,
                    str(payload.get("artifact_kind") or ""),
                    str(payload.get("artifact_locator") or ""),
                    str(payload.get("artifact_hash") or "") if payload.get("artifact_hash") is not None else None,
                ),
            )

        conn.commit()


def load_decision(*, db_path: Path, decision_id: str) -> dict[str, Any] | None:
    with _connect(db_path) as conn:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT * FROM fuzzymodo_decision_ledger WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
        if row is None:
            return None

        reasons = [
            dict(r)
            for r in conn.execute(
                """
                SELECT ref_order, reason_code, detail
                FROM fuzzymodo_decision_ledger_reason_codes
                WHERE decision_id = ?
                ORDER BY ref_order
                """,
                (decision_id,),
            ).fetchall()
        ]
        artifacts = [
            dict(r)
            for r in conn.execute(
                """
                SELECT ref_order, artifact_kind, artifact_locator, artifact_hash
                FROM fuzzymodo_decision_ledger_artifacts
                WHERE decision_id = ?
                ORDER BY ref_order
                """,
                (decision_id,),
            ).fetchall()
        ]

        out = dict(row)
        out["reason_codes"] = reasons
        out["artifacts"] = artifacts
        return out
