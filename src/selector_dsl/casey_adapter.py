"""Casey-specific advisory adapter for fuzzymodo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _stable_hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CandidateScore:
    fv_id: str
    score: float
    reason_codes: tuple[str, ...]


def _score_candidate(
    candidate: dict[str, Any],
    *,
    selected_fv_id: str | None,
    prefer_author: str | None,
) -> CandidateScore:
    fv_id = str(candidate["fv_id"])
    author = candidate.get("author")

    score = 0.5
    reasons: list[str] = []

    if selected_fv_id and fv_id == selected_fv_id:
        score += 0.2
        reasons.append("current_selection")

    if prefer_author and author == prefer_author:
        score += 0.2
        reasons.append("preferred_author")

    if candidate.get("base_fv_id"):
        score += 0.05
        reasons.append("has_lineage")

    tie = int(_stable_hash({"fv_id": fv_id})[:8], 16) / 0xFFFFFFFF
    score += tie * 0.01
    reasons.append("stable_tiebreak")

    return CandidateScore(
        fv_id=fv_id,
        score=round(score, 6),
        reason_codes=tuple(reasons),
    )


def _gap_payload(path_entry: dict[str, Any]) -> dict[str, Any]:
    candidate_count = int(path_entry.get("candidate_count", 0))
    if candidate_count <= 1:
        return {
            "gap_kind": "none",
            "severity": "none",
            "explanation": "path is resolved",
        }
    severity = "medium" if candidate_count == 2 else "high"
    noun = "candidate" if candidate_count == 1 else "candidates"
    return {
        "gap_kind": "candidate_divergence",
        "severity": severity,
        "explanation": f"{candidate_count} viable {noun} remain unresolved",
    }


def evaluate_casey_export(
    casey_export: dict[str, Any],
    *,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Consume `casey.facts.v1` and emit `fuzzymodo.casey.advisory.v1`."""

    export_version = casey_export.get("casey_export_version")
    if export_version != "casey.facts.v1":
        raise ValueError(f"Unsupported Casey export version: {export_version!r}")

    workspace = casey_export.get("workspace") or {}
    policy = workspace.get("policy") or {}
    prefer_author = policy.get("prefer_author")
    selection_rows = workspace.get("selection") or []
    selection_by_path = {
        str(row["path"]): str(row["selected_fv_id"])
        for row in selection_rows
        if "path" in row and "selected_fv_id" in row
    }

    path_results: list[dict[str, Any]] = []
    for path_entry in sorted(casey_export.get("paths") or [], key=lambda item: str(item["path"])):
        path = str(path_entry["path"])
        selected_fv_id = path_entry.get("selected_fv_id") or selection_by_path.get(path)
        candidates = path_entry.get("candidates") or []
        scored = [
            _score_candidate(
                candidate,
                selected_fv_id=selected_fv_id,
                prefer_author=prefer_author,
            )
            for candidate in candidates
        ]
        scored_sorted = sorted(scored, key=lambda item: (-item.score, item.fv_id))
        path_results.append(
            {
                "path": path,
                "recommended_fv_id": scored_sorted[0].fv_id if scored_sorted else None,
                "candidate_rankings": [
                    {
                        "fv_id": item.fv_id,
                        "score": item.score,
                        "reason_codes": list(item.reason_codes),
                    }
                    for item in scored_sorted
                ],
                "gap": _gap_payload(path_entry),
            }
        )

    if evaluated_at is None:
        evaluated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "fuzzymodo_result_version": "fuzzymodo.casey.advisory.v1",
        "tree_id": casey_export.get("tree_id"),
        "workspace_id": workspace.get("ws_id"),
        "path_results": path_results,
        "evaluated_at": evaluated_at,
        "evaluation_digest": _stable_hash(
            {
                "tree_id": casey_export.get("tree_id"),
                "workspace_id": workspace.get("ws_id"),
                "path_results": path_results,
            }
        ),
    }
