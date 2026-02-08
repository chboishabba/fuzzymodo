# Changelog

## 2026-02-07
- Implemented selector evaluator composition semantics for `all_of`, `any_of`,
  and `not`, including operator-map predicates (`eq`, `neq`, `lt`, `lte`, `gt`,
  `gte`, `in`, `startswith`, `matches`, `exists`).
- Added speculative-branch primitives and normative retirement state transitions
  in `src/selector_dsl/speculation.py`.
- Added evaluator and speculation tests (`tests/test_evaluator.py`,
  `tests/test_speculation.py`) and kept schema smoke tests passing.
