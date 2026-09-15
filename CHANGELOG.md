# Changelog

## 0.2.0 — 2026-09-15

### Breaking / correctness
- **Cut semantics:** PDP-gated edges are removed; violation iff residual closure is still `(1,1,1)`. Deleted `_all_paths_have_pdp` (which incorrectly required every edge gated).
- **Flow-type masks:** `Edge.flow_type` now masks which bits propagate. Removed `Vertex.contributes`.
- **Schema:** ACM schema moved to `schemas/v0.1/` with resolvable `$id` on `raw.githubusercontent.com` @ `v0.2.0`.

### Added
- Multi-hop fixtures/tests: `multihop_gated` / `multihop_open` (single gate on only path is sufficient).

## 0.1.0 — 2026-09-15

- Initial public research prototype
