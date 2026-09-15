# mesa-ibi-scanner

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-research%20prototype-orange)](#disclaimer)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22744547.svg)](https://doi.org/10.5281/zenodo.22744547)

**Research prototype** that evaluates **MESA Invariant 1** — directed inbound trifecta closure \(\mathrm{Cl}(b)\) — over a typed agent/service interaction graph.

MESA plugs into frameworks CISOs already run. Public surface: **MESA-IBI**, **MESA-ACM**, **MESA-ACA**, and **Invariant 1**. This repo ships the **scanner sketch + ACM JSON Schema**.

> **Disclaimer:** Not production policy enforcement. No exploit recipes. Toy fixtures are *shaped like* public Hugging Face Artifactory / DseWiki *composition lessons* for unit tests only.

## Why it exists

Per-agent checks (Rule of Two / lethal trifecta) can all pass while a **group** of agents plus a shared interaction surface still compose \((1,1,1)\). This tool computes inbound closure and flags agents where \(\mathrm{Cl}(b)=(1,1,1)\) without a PDP gate on contributing paths (`MESA-INV-01`).

Paper: https://doi.org/10.5281/zenodo.22744547

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
mesa-ibi-scan --fixture dsewiki_like --json
pytest -q
```

## Property vector

`(private_data, untrusted_content, external_communication)` ∈ `{0,1}³`  
Join is bitwise OR along directed paths **into** agent `b` (including typed services on those paths).

## Companion schema

- `schemas/mesa-acm.schema.json` — Agency Capability Manifest (ACM)
- `schemas/examples/` — signed-admit / unsigned-deny style examples

## What it does *not* do

- Live estate scanning or weaponized Schelling-point discovery
- Measured false-positive rates (flow typing is illustrative)
- Replace your PDP / mesh / ACM admission path

## Cite

See [`CITATION.cff`](CITATION.cff). Prefer the Zenodo DOI for the paper.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

## Topics (GitHub)

`agentic-ai` `cybersecurity` `multi-agent` `zero-trust` `policy-as-code` `research`
