## 0.4.0 — 2026-09-26

### Added (graded lattice, TASK-0007, docs/LATTICE.md)
- `mesa_ibi_scanner.lattice`: four-level P/U/E closure with flow caps, per-edge caps (scoped OBO tokens), zone thresholds from the protected `thresholds/zones.json`, INV01 and NEAR_MISS findings, witness paths, minimal cuts, `IncrementalClosure`.
- Closure frontier export (`--frontier-out`) with a content-derived `frontier_version` and optional Ed25519 signature (`--sign-key`, extra `sign`).
- Schema v0.2 (`schemas/v0.2/mesa-topology.schema.json`) and frontier schema; v0.1 documents are auto-promoted (bit 1 -> level 3).
- `--lattice` flag; v0.2 input selects lattice mode automatically. SARIF adds `MESA-INV-01-NEAR-MISS` warnings.
- Temporal closure behind `--timeline` (docs/TEMPORAL.md, TASK-0008): per-agent memory window W; only attested wipes reset; P-08, SC-03, SC-10.
- 84 lattice golden fixtures, property tests P-01 to P-05, P-07, P-10 to P-12 at 10,000 cases, B-01 benchmark.

### Fixed
- Schemas and thresholds are packaged under `mesa_ibi_scanner/data/`, so a non-editable install can validate `--input` (v0.3.2 could not find its schema outside a checkout).

### Unchanged
- v0.1 output for v0.1 input without `--lattice`. All 27 v0.1 tests are unmodified.

## 0.3.2 — 2026-09-16

### Performance
- Hoist `inbound_adjacency()` once per `evaluate_invariant`; compute contributors lazily only for violating agents (~5× faster at V=4000).

### Correctness / packaging
- Align `CITATION.cff` + `.zenodo.json` with package version (CI version-consistency check).
- README: GitHub `$...$` math; complexity claim scoped to closure + lazy BFS.
- Topology schema/loader: `pdp_gate` optional, default `false`.
- Property fuzz tests (monotonicity, gating soundness, all-gated, determinism) + 2k-vertex perf budget.

## 0.3.1 — 2026-09-15

- `off_inventory_vacuous` fixture + test documenting incomplete-IBI vacuous-green hazard (Sim 6 / F-E5 class).
- JSON output adds `residual_cut_ok` (alias of legacy `pdp_on_all_contributing_paths`).

# Changelog

## 0.3.0 — 2026-09-15

### Added (toolization)
- **Topology ingestion:** `schemas/v0.1/mesa-topology.schema.json` + `--input topology.json` (jsonschema-validated).
- Example: `schemas/examples/topology-hf-like.json` matching `hf_like` fixture behavior.
- **CI output:** `--format text|json|sarif` (minimal SARIF 2.1.0 for violations), `--exit-code` (non-zero on violation).
- `--severity` stub accepted but filtering deferred (documented).
- GitHub Actions CI (pytest on Python 3.10–3.13).
- `RELATED.md` (paper DOI ↔ scanner relation; software DOI TODO).

### Changed
- Version bump to **0.3.0** for toolization release.
- Dependency: `jsonschema>=4.18`.

## 0.2.0 — 2026-09-15

### Breaking / correctness
- **Cut semantics:** PDP-gated edges are removed; violation iff residual closure is still `(1,1,1)`. Deleted `_all_paths_have_pdp` (which incorrectly required every edge gated).
- **Flow-type masks:** `Edge.flow_type` now masks which bits propagate. Removed `Vertex.contributes`.
- **Schema:** ACM schema moved to `schemas/v0.1/` with resolvable `$id` on `raw.githubusercontent.com` @ `v0.2.0`.

### Added
- Multi-hop fixtures/tests: `multihop_gated` / `multihop_open` (single gate on only path is sufficient).

## 0.1.0 — 2026-09-15

- Initial public research prototype
