# mesa-ibi-scanner

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-research%20prototype-orange)](#disclaimer)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22744547.svg)](https://doi.org/10.5281/zenodo.22744547)

**Research prototype** that evaluates **MESA Invariant 1** — directed inbound trifecta closure \(\mathrm{Cl}(b)\) — over a typed agent/service interaction graph, with **PDP cut semantics**.

> **Disclaimer:** Not production policy enforcement. No exploit recipes. Toy fixtures are *shaped like* public Hugging Face Artifactory / DseWiki *composition lessons* for unit tests only.

Paper: https://doi.org/10.5281/zenodo.22744547

## Invariant 1 (cut semantics)

For every agent \(b\), let \(\mathrm{Cl}(b)\) be the join of property vectors over vertices with a directed path into \(b\), **masked by edge flow type**. PDP-gated edges are **removed**; the gated set must form a **cut** such that closure over the **residual** graph is not \((1,1,1)\).

Complexity: \(O(|V|\cdot|E|)\) reachability fixpoint (not \(2^{|V|}\)).

## Install

```bash
git clone https://github.com/uddeshya-world/mesa-ibi-scanner.git
cd mesa-ibi-scanner
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick start

```bash
mesa-ibi-scan --fixture hf_like
mesa-ibi-scan --fixture multihop_gated
mesa-ibi-scan --fixture multihop_open --json
pytest -q
```

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

## Companion schema

- Versioned: [`schemas/v0.1/mesa-acm.schema.json`](schemas/v0.1/mesa-acm.schema.json)
- `$id`: `https://raw.githubusercontent.com/uddeshya-world/mesa-ibi-scanner/v0.2.0/schemas/v0.1/mesa-acm.schema.json`
- Examples under `schemas/examples/`

## What it does *not* do

- Live estate scanning or weaponized Schelling-point discovery
- Measured false-positive rates
- Replace your PDP / mesh / ACM admission path

## License

Apache License 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
