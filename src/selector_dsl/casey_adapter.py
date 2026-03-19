"""Casey-specific advisory adapter for fuzzymodo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _stable_hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CandidateScore:
    fv_id: str
    score: float
    reason_codes: tuple[str, ...]


def _normalized_features(candidate: Mapping[str, Any]) -> dict[str, Any]:
    raw = candidate.get("features")
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): raw[key] for key in sorted(raw)}


def _feature_signal(candidate: Mapping[str, Any]) -> int:
    features = _normalized_features(candidate)
    return sum(
        1
        for key, value in features.items()
        if key != "_version" and value not in (None, "", [], {}, ())
    )


def _score_candidate(
    candidate: Mapping[str, Any],
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

    feature_signal = _feature_signal(candidate)
    if feature_signal:
        score += min(0.1, feature_signal * 0.02)
        reasons.append("feature_context")

    tie = int(_stable_hash({"fv_id": fv_id})[:8], 16) / 0xFFFFFFFF
    score += tie * 0.01
    reasons.append("stable_tiebreak")

    return CandidateScore(
        fv_id=fv_id,
        score=round(score, 6),
        reason_codes=tuple(reasons),
    )


def _feature_gap_items(candidates: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    feature_values: dict[str, set[str]] = {}
    for candidate in candidates:
        for key, value in _normalized_features(candidate).items():
            if key == "_version":
                continue
            feature_values.setdefault(key, set()).add(_canonical_json(value))

    varying_keys = sorted(key for key, values in feature_values.items() if len(values) > 1)
    if not varying_keys:
        return []

    keys_for_payload = varying_keys[:3]
    summary = ", ".join(keys_for_payload)
    detail = f"candidate feature context differs across {summary}"
    if len(varying_keys) > len(keys_for_payload):
        detail += f" (+{len(varying_keys) - len(keys_for_payload)} more)"
    return [
        {
            "kind": "feature_context_divergence",
            "detail": detail,
            "feature_keys": keys_for_payload,
        }
    ]


def _gap_payload(
    path_entry: Mapping[str, Any],
    *,
    recommended_fv_id: str | None,
) -> dict[str, Any]:
    candidate_count = int(path_entry.get("candidate_count", 0))
    if candidate_count <= 1:
        return {
            "gap_kind": "none",
            "severity": "none",
            "explanation": "path is resolved",
            "primary_axis": "resolved",
            "gap_items": [],
            "suggested_actions": [],
        }
    candidates = [
        candidate
        for candidate in (path_entry.get("candidates") or [])
        if isinstance(candidate, Mapping)
    ]
    gap_items: list[dict[str, Any]] = [
        {
            "kind": "unresolved_multiplicity",
            "detail": f"{candidate_count} viable candidates remain live for this path",
            "candidate_count": candidate_count,
        }
    ]
    suggestions = ["keep candidates live until the divergence is resolved"]
    primary_axis = "candidate_count"

    authors = sorted({str(candidate.get("author")) for candidate in candidates if candidate.get("author")})
    if len(authors) > 1:
        gap_items.append(
            {
                "kind": "author_divergence",
                "detail": "candidate provenance spans multiple authors",
                "authors": authors,
            }
        )
        suggestions.append("inspect author-origin differences before collapse")
        primary_axis = "author"

    base_ids = sorted(
        {
            str(candidate.get("base_fv_id"))
            for candidate in candidates
            if candidate.get("base_fv_id") is not None
        }
    )
    lineage_present = any(candidate.get("base_fv_id") is not None for candidate in candidates)
    if len(base_ids) > 1 or (lineage_present and any(candidate.get("base_fv_id") is None for candidate in candidates)):
        gap_items.append(
            {
                "kind": "lineage_divergence",
                "detail": "candidates do not share a single lineage anchor",
                "base_fv_ids": base_ids,
            }
        )
        suggestions.append("compare lineage anchors or synthesize a merged candidate")
        primary_axis = "lineage"

    feature_items = _feature_gap_items(candidates)
    if feature_items:
        gap_items.extend(feature_items)
        suggestions.append("inspect feature-bag differences before collapse")
        if primary_axis in {"candidate_count", "author"}:
            primary_axis = "feature_context"

    selected_fv_id = path_entry.get("selected_fv_id")
    if selected_fv_id and recommended_fv_id and str(selected_fv_id) != str(recommended_fv_id):
        gap_items.append(
            {
                "kind": "selection_divergence",
                "detail": "current workspace selection differs from the advisory recommendation",
                "selected_fv_id": str(selected_fv_id),
                "recommended_fv_id": str(recommended_fv_id),
            }
        )
        suggestions.append("review whether the workspace selection should remain pinned")
        if primary_axis == "candidate_count":
            primary_axis = "selection"

    unique_actions = list(dict.fromkeys(suggestions))
    substantive_axes = {
        item["kind"]
        for item in gap_items
        if item["kind"] != "unresolved_multiplicity"
    }
    severity = "high" if candidate_count >= 3 or len(substantive_axes) >= 2 else "medium"
    explanation = gap_items[-1]["detail"] if gap_items else "unresolved candidate divergence remains"
    if primary_axis == "lineage":
        explanation = "candidates diverge primarily through lineage differences"
    elif primary_axis == "feature_context":
        explanation = "candidates diverge primarily through feature-context differences"
    elif primary_axis == "author":
        explanation = "candidates diverge primarily through provenance differences"
    elif primary_axis == "selection":
        explanation = "current workspace selection is no longer aligned with the top advisory candidate"

    return {
        "gap_kind": "candidate_divergence",
        "severity": severity,
        "explanation": explanation,
        "primary_axis": primary_axis,
        "gap_items": gap_items,
        "suggested_actions": unique_actions,
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
        recommended_fv_id = scored_sorted[0].fv_id if scored_sorted else None
        path_results.append(
            {
                "path": path,
                "recommended_fv_id": recommended_fv_id,
                "candidate_rankings": [
                    {
                        "fv_id": item.fv_id,
                        "score": item.score,
                        "reason_codes": list(item.reason_codes),
                    }
                    for item in scored_sorted
                ],
                "gap": _gap_payload(
                    path_entry,
                    recommended_fv_id=recommended_fv_id,
                ),
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
