# Changelog

## 2026-03-19
- Added a suite-level planning reference for the Casey -> fuzzymodo contract
  (`docs/planning/casey_fuzzymodo_interface_contract_20260319.md`) to lock the
  expected Casey lattice export and fuzzymodo advisory result shape before
  implementation.
- Implemented a minimal Casey-specific advisory adapter in
  `src/selector_dsl/casey_adapter.py` consuming `casey.facts.v1` and emitting
  `fuzzymodo.casey.advisory.v1` with deterministic rankings, gap payloads, and
  an `evaluation_digest`.
- Added tests for deterministic Casey advisory output and Casey CLI export
  roundtrip consumption.

## 2026-03-09
- Clarified the intended `fuzzymodo -> StatiBaker` seam as observer-only via
  suite planning note `docs/planning/fuzzymodo_statiBaker_interface_20260309.md`.
- Recast that seam as DB-backed rather than JSON-first:
  SB-owned overlay extension tables plus a separate read-only decision ledger
  that SB may reference without owning selector/norm authority.
- Updated `docs/interfaces.md` and `README.md` to distinguish the currently
  implemented selector primitives (hashing, boolean evaluation,
  speculation/retirement) from the fuller planned decision-record/replay
  interface.

## 2026-02-07
- Implemented selector evaluator composition semantics for `all_of`, `any_of`,
  and `not`, including operator-map predicates (`eq`, `neq`, `lt`, `lte`, `gt`,
  `gte`, `in`, `startswith`, `matches`, `exists`).
- Added speculative-branch primitives and normative retirement state transitions
  in `src/selector_dsl/speculation.py`.
- Added evaluator and speculation tests (`tests/test_evaluator.py`,
  `tests/test_speculation.py`) and kept schema smoke tests passing.
