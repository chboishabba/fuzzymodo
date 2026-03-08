# Changelog

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
