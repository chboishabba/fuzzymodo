# Fuzzymodo

Implementation scaffold for the selector DSL and norm-constraint execution
pipeline discussed in `OSS-Fuzz Bug Detection`.

## Layout
- `src/selector_dsl/`: canonicalization, selector evaluation, and speculation
  helpers.
- `tests/`: schema smoke + evaluator/speculation tests.
- `docs/interfaces.md`: intended intersections, interaction flow, and exchange
  channels.

## Intended Intersections
- Planning contracts in `docs/planning/fuzzymodo/` are authoritative for DSL and
  norm payload shape.
- `casey-git-clone/` can provide candidate/version facts for selector
  evaluation in future integration work.
- ITIR suite consumers can use selector decisions as context for downstream
  ranking and triage workflows.
- The current `fuzzymodo -> StatiBaker` seam is observer-only and documented in
  `../docs/planning/fuzzymodo_statiBaker_interface_20260309.md`; it is a
  DB-backed contract clarification, not a finished adapter.

## Interaction Flow
1. Receive selector + optional norm-constraint payloads.
2. Validate against planning schemas.
3. Canonicalize selector payload for deterministic hashing/replay.
4. Evaluate clauses against graph-scoped facts.
5. Emit selection decision payloads with stable provenance metadata.

## Exchange Channels
- Input channel: selector payload JSON (see
  `docs/planning/fuzzymodo/selector_dsl.schema.json`).
- Input channel: norm constraint JSON (see
  `docs/planning/fuzzymodo/norm_constraint.schema.json`).
- Output channel: canonical selector hash + normalized selector JSON.
- Output channel: evaluation result bundle (`matched`, matched clauses,
  rejection reasons).

## Current Status
Core evaluator and speculation primitives are implemented. Parser/norm
invalidation integration remains open. Full decision-record egress and the
dedicated `StatiBaker` observer adapter remain planned rather than completed.
