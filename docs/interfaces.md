# Fuzzymodo Interface Contract (Intended)

## 1. Intersections
- Planning source of truth:
  `docs/planning/fuzzymodo/selector_dsl.schema.json`,
  `docs/planning/fuzzymodo/norm_constraint.schema.json`,
  `docs/planning/fuzzymodo/canonical_hashing.md`.
- Upstream facts providers:
  graph fact emitters in ITIR-suite components (including future
  `casey-git-clone/` adapters).
- Downstream consumers:
  ranking, triage, and replay tools that require deterministic selector
  decisions.

## 2. Interaction Model
1. Parse and validate selector payload.
2. Parse and validate norm-constraint payload (optional).
3. Canonicalize selector payload to stable representation.
4. Hash canonical payload for replay key.
5. Evaluate payload against graph-scoped facts.
6. Apply norm constraints for invalidation or replay gating.
7. Emit deterministic decision record.

## 3. Exchange Channels

### Channel A: Selector Ingress
- Transport: JSON object in-process (initial MVP).
- Contract: `selector_dsl.schema.json`.
- Required fields: `dsl_version` and one of `all_of`, `any_of`, `not`.
- Failure mode: schema reject with explicit field-level errors.

### Channel B: Norm Constraint Ingress
- Transport: JSON object in-process (initial MVP).
- Contract: `norm_constraint.schema.json`.
- Role: constrain selector acceptance, replay eligibility, and freshness.
- Failure mode: reject with constraint validation errors.

### Channel C: Facts Evaluation Feed
- Transport: Python mapping/list structures in MVP; file/IPC adapter later.
- Shape: graph-layered facts keyed by clause fields (for example
  `structural.function.name`, `execution.entrypoint`).
- Failure mode: unknown graph or unknown field reported without mutation.

### Channel D: Decision Egress
- Transport: structured JSON-serializable result.
- Intended fields:
  `selector_hash`, `matched`, `matched_clauses`, `rejected_clauses`,
  `errors`, `evaluated_at`.
- Stability goal: same selector + same facts -> same result payload.

### Channel E: Replay Artifact
- Transport: file artifact (future default path:
  `artifacts/fuzzymodo/runs/<timestamp>/`).
- Contents: canonical selector JSON, hash, input fact digest, result payload.
- Purpose: deterministic replay and forensic diffing.
