# mesa-ibi-scanner

[![CI](https://github.com/uddeshya-world/mesa-ibi-scanner/actions/workflows/ci.yml/badge.svg)](https://github.com/uddeshya-world/mesa-ibi-scanner/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-research%20prototype-orange)](#disclaimer)
[![Paper DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22743175.svg)](https://doi.org/10.5281/zenodo.22743175)
[![Software DOI](https://img.shields.io/badge/Software%20DOI-pending%20Zenodo--GitHub%20enable-lightgrey)](#software-doi-pending--do-not-invent)

**Research prototype** that evaluates **MESA Invariant 1** — directed inbound trifecta closure $\mathrm{Cl}(b)$ — over a typed agent/service interaction graph, with **PDP cut semantics**.

> **Disclaimer:** Not production policy enforcement. No exploit recipes. Toy fixtures are *shaped like* public Hugging Face Artifactory / DseWiki *composition lessons* for unit tests only.

**Paper DOI** (concept / stable cite): https://doi.org/10.5281/zenodo.22743175  
**Paper version DOI** (current record; the concept DOI above is the preferred citation): https://doi.org/10.5281/zenodo.22761743  
**Software DOI:** pending Zenodo-GitHub enable (do not invent; not minted yet)  
Release: **v0.3.2** (toolization — topology `--input`, CI formats, exit codes)

## Invariant 1 (cut semantics)

For every agent $b$, let $\mathrm{Cl}(b)$ be the join of property vectors over vertices with a directed path into $b$, **masked by edge flow type**. PDP-gated edges are **removed**; the gated set must form a **cut** such that closure over the **residual** graph is not $(1,1,1)$.

Complexity: `evaluate_invariant` is $O(|V|\cdot|E|)$ for the two closure fixpoints (not $2^{|V|}$), plus a reverse BFS only for agents that violate. `compute_inbound_closure` alone is $O(|V|\cdot|E|)$.

## Install

```bash
git clone https://github.com/uddeshya-world/mesa-ibi-scanner.git
cd mesa-ibi-scanner
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick start

```bash
# Built-in fixtures
mesa-ibi-scan --fixture hf_like
mesa-ibi-scan --fixture multihop_gated
mesa-ibi-scan --fixture multihop_open --format json

# Topology file (schema-validated)
mesa-ibi-scan --input schemas/examples/topology-hf-like.json --format text

# CI-friendly: non-zero exit on violation + SARIF
mesa-ibi-scan --input schemas/examples/topology-hf-like.json --format sarif --exit-code

pytest -q
```

### CLI flags (v0.3)

| Flag | Meaning |
|---|---|
| `--fixture NAME` | Built-in toy graph (default `hf_like` if neither fixture nor input) |
| `--input PATH` | Load / validate estate topology JSON |
| `--format text\|json\|sarif` | Output format (minimal SARIF 2.1.0 for violations) |
| `--exit-code` | Exit `1` if any INV-01 violation; schema/load errors → `2` |
| `--severity error\|warning\|note` | **Stub / deferred** — accepted for forward-compat; all violations are `error` today; no filtering yet |

## Flow-type masks (illustrative / uncalibrated)

| `flow_type` | Mask `(P,U,E)` | Rationale (prototype) |
|---|---|---|
| `write` | `(1,1,1)` | Full state transfer |
| `goal-message` | `(0,1,0)` | Conveys untrusted content / intent, not data or egress |
| `proxy/egress` | `(0,0,1)` | Conveys reachability / egress capability only |
| `identity-mint` | `(1,0,1)` | Credential / identity capability |
| `read` | `(1,1,0)` | Data + content, not egress capability |

These masks are **not** a measured false-positive model. They replace the old hand-tuned `Vertex.contributes` flag.

## Property vector

`(private_data, untrusted_content, external_communication)` ∈ `{0,1}³`

## Companion schemas

- ACM (versioned): [`schemas/v0.1/mesa-acm.schema.json`](schemas/v0.1/mesa-acm.schema.json)
- Topology (v0.3): [`schemas/v0.1/mesa-topology.schema.json`](schemas/v0.1/mesa-topology.schema.json)
  - `$id`: `https://raw.githubusercontent.com/uddeshya-world/mesa-ibi-scanner/v0.3.0/schemas/v0.1/mesa-topology.schema.json`
- Example topology: [`schemas/examples/topology-hf-like.json`](schemas/examples/topology-hf-like.json) (matches `hf_like` fixture)

## Related works (paper ↔ scanner)

See [`RELATED.md`](RELATED.md). Summary:

- **Paper** (version `10.5281/zenodo.22761743`; concept `10.5281/zenodo.22743175`) **isSupplementedBy** this scanner (reference implementation).
- **Scanner** **isSupplementTo** the paper (see `.zenodo.json` `related_identifiers`).
- Once a **software DOI** is minted, point the paper’s related-works link at that DOI (not the paper DOI reused as software).

### Software DOI (pending — do not invent)

<a id="software-doi-pending--do-not-invent"></a>

A dedicated **software** Zenodo DOI for this repository is **pending Zenodo-GitHub enable** — it is **not** minted yet. The paper DOI above is **not** the software DOI.

Exact enablement steps (webhook + tagged release): [Zenodo — Enable a repository](https://help.zenodo.org/docs/github/enable-repository/) and [Describe software](https://help.zenodo.org/docs/github/describe-software/).

1. Sign in at [zenodo.org](https://zenodo.org) with the GitHub account that owns `uddeshya-world/mesa-ibi-scanner`.
2. Zenodo → profile → **GitHub** → **Sync now** → toggle **ON** for this repo (installs the release webhook).
3. Publish a **new** GitHub Release **after** the toggle (Zenodo does not auto-import past releases such as existing `v0.3.0`).
4. Copy the software DOI Zenodo mints; update this README badge, `CITATION.cff` `identifiers`, and paper related works. Keep the concept DOI `10.5281/zenodo.22743175` as `preferred-citation` (it resolves to the current version DOI `10.5281/zenodo.22761743`).

## What it does *not* do

- Live estate scanning or weaponized Schelling-point discovery
- Measured false-positive rates
- Replace your PDP / mesh / ACM admission path

## License

Apache License 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
