from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .decision_ledger_sqlite import DecisionLedgerRecord, upsert_decision
from .exchange import DecisionEgress, evaluate_to_decision_egress
from .replay_artifacts import write_replay_bundle


def _stable_hash(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _coerce_mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _proposal_id(kind: str, target: str) -> str:
    return "proposal:" + hashlib.sha256(f"{kind}|{target}".encode("utf-8")).hexdigest()[:16]


def selector_graph_facts_from_codex_trace(facts: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    graphs = facts.get("graphs")
    trace_scope = _coerce_mapping(facts.get("trace_scope"))
    session = _coerce_mapping(facts.get("session"))
    message_flow = _coerce_mapping(facts.get("message_flow"))
    tool_use = _coerce_mapping(facts.get("tool_use"))
    outcomes = _coerce_mapping(facts.get("outcomes"))
    artifacts = _coerce_mapping(facts.get("artifacts"))
    if isinstance(graphs, Mapping):
        trace_scope = _coerce_mapping(graphs.get("trace_scope")) or trace_scope
        session = _coerce_mapping(graphs.get("session")) or session
        message_flow = _coerce_mapping(graphs.get("message_flow")) or message_flow
        tool_use = _coerce_mapping(graphs.get("tool_use")) or tool_use
        outcomes = _coerce_mapping(graphs.get("outcomes")) or outcomes
        artifacts = _coerce_mapping(graphs.get("artifacts")) or artifacts

    # Map the Codex-trace contract onto the currently valid selector graph set.
    timeline = dict(trace_scope)
    timeline.update(message_flow)

    return {
        "timeline": timeline,
        "execution": tool_use,
        "ecosystem": session,
        "normative": outcomes,
        "build": artifacts,
    }


@dataclass(frozen=True)
class CodexTraceDecision:
    decision_egress: DecisionEgress
    fact_digest: str
    evaluation_digest: str
    evaluation_mode: str
    branch_review_classification: str | None
    reason_codes: list[dict[str, Any]]
    evidence_refs: list[dict[str, Any]]
    proposals: list[dict[str, Any]]


def _derive_proposals(facts: Mapping[str, Any]) -> list[dict[str, Any]]:
    outcomes = _coerce_mapping(facts.get("outcomes"))
    evidence_refs = [dict(item) for item in facts.get("evidence_refs", []) if isinstance(item, Mapping)]
    proposals: list[dict[str, Any]] = []

    for item in outcomes.get("completion_candidates", []) if isinstance(outcomes.get("completion_candidates"), list) else []:
        if not isinstance(item, Mapping):
            continue
        target = str(item.get("candidate_id") or item.get("external_item_id") or "")
        if not target:
            continue
        proposals.append(
            {
                "proposal_id": _proposal_id("completion_candidate", target),
                "proposal_kind": "completion_candidate",
                "target_kind": "external_commitment",
                "target_locator": target,
                "rationale_code": "candidate_completion_from_trace",
                "evidence_refs": evidence_refs[:3],
            }
        )

    for item in outcomes.get("open_commitments", []) if isinstance(outcomes.get("open_commitments"), list) else []:
        if not isinstance(item, Mapping):
            continue
        target = str(item.get("external_item_id") or item.get("candidate_id") or "")
        if not target:
            continue
        proposals.append(
            {
                "proposal_id": _proposal_id("followup_task", target),
                "proposal_kind": "followup_task",
                "target_kind": "external_commitment",
                "target_locator": target,
                "rationale_code": "open_commitment_without_completion",
                "evidence_refs": evidence_refs[:3],
            }
        )

    for idx, item in enumerate(outcomes.get("evidence_gaps", []) if isinstance(outcomes.get("evidence_gaps"), list) else []):
        detail = str(item.get("reason") or item.get("warning") or f"gap-{idx}") if isinstance(item, Mapping) else f"gap-{idx}"
        proposals.append(
            {
                "proposal_id": _proposal_id("evidence_gap", detail),
                "proposal_kind": "evidence_gap",
                "target_kind": "trace_scope",
                "target_locator": detail,
                "rationale_code": "trace_gap_requires_review",
                "evidence_refs": evidence_refs[:3],
            }
        )
    return proposals


def _classify_backward_review(
    *,
    matched: bool,
    facts: Mapping[str, Any],
    outcome_hint: Mapping[str, Any] | None,
    proposals: list[dict[str, Any]],
) -> str:
    outcomes = _coerce_mapping(facts.get("outcomes"))
    blockers = outcomes.get("unresolved_blockers") if isinstance(outcomes.get("unresolved_blockers"), list) else []
    completed = outcomes.get("completed_commitments") if isinstance(outcomes.get("completed_commitments"), list) else []
    completion_candidates = (
        outcomes.get("completion_candidates") if isinstance(outcomes.get("completion_candidates"), list) else []
    )
    hint = _coerce_mapping(outcome_hint)
    target = str(hint.get("target_locator") or hint.get("target_id") or "")

    if blockers:
        return "blocked_by_missing_evidence"
    if not matched:
        return "unsupported_by_trace"
    if target and any(str(item.get("external_item_id") or item.get("candidate_id") or "") == target for item in completed if isinstance(item, Mapping)):
        return "superseded"
    if target and any(str(item.get("candidate_id") or item.get("external_item_id") or "") == target for item in completion_candidates if isinstance(item, Mapping)):
        return "seen_but_rejected_with_support"
    if target and any(str(item.get("target_locator") or "") == target for item in proposals):
        return "missed_with_support"
    if proposals:
        return "missed_with_support"
    return "unsupported_by_trace"


def evaluate_codex_trace(
    selector_payload: Mapping[str, Any],
    *,
    facts: Mapping[str, Any],
    evaluation_mode: str = "forward_state_build",
    outcome_hint: Mapping[str, Any] | None = None,
    norm_constraints: list[Mapping[str, Any]] | None = None,
) -> CodexTraceDecision:
    graph_facts = selector_graph_facts_from_codex_trace(facts)
    decision = evaluate_to_decision_egress(
        selector_payload,
        facts=graph_facts,
        norm_constraints=norm_constraints,
    )
    evidence_refs = [dict(item) for item in facts.get("evidence_refs", []) if isinstance(item, Mapping)]
    proposals = _derive_proposals(facts)
    reason_codes: list[dict[str, Any]] = [{"reason_code": "trace_mode", "detail": evaluation_mode}]
    for error in decision.errors:
        reason_codes.append({"reason_code": "eval_error", "detail": str(error)})
    if proposals:
        reason_codes.append({"reason_code": "proposal_count", "detail": str(len(proposals))})
    if evidence_refs:
        reason_codes.append({"reason_code": "evidence_ref_count", "detail": str(len(evidence_refs))})

    classification = None
    if evaluation_mode == "backward_branch_review":
        classification = _classify_backward_review(
            matched=decision.matched,
            facts=facts,
            outcome_hint=outcome_hint,
            proposals=proposals,
        )
        reason_codes.append({"reason_code": "branch_review_classification", "detail": classification})

    fact_digest = str(facts.get("fact_digest") or _stable_hash(facts))
    evaluation_digest = _stable_hash(
        {
            "selector_hash": decision.selector_hash,
            "fact_digest": fact_digest,
            "evaluation_mode": evaluation_mode,
            "classification": classification,
            "proposal_ids": [str(item.get("proposal_id") or "") for item in proposals],
        }
    )
    return CodexTraceDecision(
        decision_egress=decision,
        fact_digest=fact_digest,
        evaluation_digest=evaluation_digest,
        evaluation_mode=evaluation_mode,
        branch_review_classification=classification,
        reason_codes=reason_codes,
        evidence_refs=evidence_refs,
        proposals=proposals,
    )


def codex_trace_decision_to_sb_overlay_record(
    decision: CodexTraceDecision,
    *,
    activity_event_id: str,
    annotation_id: str,
    state_date: str,
    provenance: Mapping[str, Any],
    decision_state: str,
    policy_hash: str | None = None,
    replay_key: str | None = None,
    decision_ledger_id: str | None = None,
    artifacts: list[Mapping[str, Any]] | None = None,
    status: str | None = None,
    confidence: str | None = None,
) -> dict[str, Any]:
    selector_refs = [
        {
            "selector_hash": decision.decision_egress.selector_hash,
            "decision_state": decision_state,
            "matched": 1 if decision.decision_egress.matched else 0,
            "policy_hash": policy_hash,
            "replay_key": replay_key,
            "created_at": decision.decision_egress.evaluated_at,
        }
    ]
    artifact_refs: list[dict[str, Any]] = []
    if decision_ledger_id:
        artifact_refs.append(
            {
                "artifact_kind": "decision_ledger_ref",
                "artifact_locator": f"fuzzymodo_decision_ledger:{decision_ledger_id}",
                "artifact_hash": None,
            }
        )
    for item in decision.proposals:
        artifact_refs.append(
            {
                "artifact_kind": "codex_trace_proposal",
                "artifact_locator": str(item.get("proposal_id") or ""),
                "artifact_hash": None,
            }
        )
    for item in artifacts or []:
        if not isinstance(item, Mapping):
            continue
        artifact_refs.append(
            {
                "artifact_kind": str(item.get("artifact_kind") or ""),
                "artifact_locator": str(item.get("artifact_locator") or ""),
                "artifact_hash": item.get("artifact_hash"),
            }
        )

    overlay_provenance = dict(provenance)
    overlay_provenance.update(
        {
            "fact_contract": "codex_trace_facts_v1",
            "evaluation_mode": decision.evaluation_mode,
            "evaluation_digest": decision.evaluation_digest,
            "fact_digest": decision.fact_digest,
            "branch_review_classification": decision.branch_review_classification,
        }
    )

    return {
        "activity_event_id": str(activity_event_id),
        "annotation_id": str(annotation_id),
        "provenance": overlay_provenance,
        "state_date": str(state_date),
        "observer_kind": "fuzzymodo_codex_trace_v1",
        "status": status,
        "confidence": confidence,
        "selector_refs": selector_refs,
        "reason_codes": list(decision.reason_codes),
        "artifact_refs": artifact_refs,
        "evidence_refs": list(decision.evidence_refs),
    }


def emit_codex_trace_observer_artifacts(
    *,
    decision_ledger_db_path: Path,
    decision_id: str,
    selector_payload: Mapping[str, Any],
    facts: Mapping[str, Any],
    activity_event_id: str,
    annotation_id: str,
    state_date: str,
    provenance: Mapping[str, Any],
    decision_state: str,
    evaluation_mode: str = "forward_state_build",
    outcome_hint: Mapping[str, Any] | None = None,
    policy_hash: str | None = None,
    replay_key: str | None = None,
    replay_out_root: Path | None = None,
) -> dict[str, Any]:
    decision = evaluate_codex_trace(
        selector_payload,
        facts=facts,
        evaluation_mode=evaluation_mode,
        outcome_hint=outcome_hint,
    )
    replay_dir = write_replay_bundle(
        decision.decision_egress,
        selector_payload=selector_payload,
        out_root=replay_out_root,
        fact_digest=decision.fact_digest,
    )
    upsert_decision(
        db_path=decision_ledger_db_path,
        record=DecisionLedgerRecord(
            decision_id=decision_id,
            selector_hash=decision.decision_egress.selector_hash,
            decision_state=decision_state,
            matched=1 if decision.decision_egress.matched else 0,
            policy_hash=policy_hash,
            replay_key=replay_key,
            fact_digest=decision.fact_digest,
            created_at=decision.decision_egress.evaluated_at,
            decided_by=None,
            source_tool="fuzzymodo.codex_trace",
        ),
        reason_codes=decision.reason_codes,
        artifacts=[
            {
                "artifact_kind": "replay_bundle_dir",
                "artifact_locator": str(replay_dir),
                "artifact_hash": None,
            }
        ],
    )
    return codex_trace_decision_to_sb_overlay_record(
        decision,
        activity_event_id=activity_event_id,
        annotation_id=annotation_id,
        state_date=state_date,
        provenance=provenance,
        decision_state=decision_state,
        policy_hash=policy_hash,
        replay_key=replay_key,
        decision_ledger_id=decision_id,
        artifacts=[
            {
                "artifact_kind": "replay_bundle_dir",
                "artifact_locator": str(replay_dir),
                "artifact_hash": None,
            }
        ],
        status=decision.branch_review_classification or evaluation_mode,
        confidence="medium",
    )
