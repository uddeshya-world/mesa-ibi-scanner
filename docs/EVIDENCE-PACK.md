# Compliance evidence pack

Status: draft for TASK-0016 (G-P3a). The G-P3 machine check: **the pack builds from CI artifacts only**. Nothing in it is written by hand after the run that produced it.

## Contents

| Part | Source | Supports (see docs/crosswalks) |
| --- | --- | --- |
| Gate evidence bundles | `evidence/*.json` from each repository's CI run | CA-2; ISO 27001 8.32; ISO 42001 A.6.2.4 |
| Committed topology and signed frontier | Scanner run on the committed topology (`--frontier-out --sign-key`) | CM-8, AC-4, AU-10 |
| Scanner report | Lattice JSON and SARIF for the committed topology | AC-4, AC-6, CM-4 |
| Decision-record sample and verification log | PEP record store, verified against the PEP public key | AU-3, AU-10, AU-12 |
| Drift findings | mesa-d shadow output for the period | CA-7, SI-4, AU-6 |
| Calibration reports | jev-eval per pinned model version (A-04) | CA-2, SA-9 |
| Crosswalks | `docs/crosswalks/*.md` at the tagged commit | all |
| Claims ledger | `claims/ledger.json` with `check-claims --rerun` output | — |

## Manifest

`manifest.json` lists every file with its SHA-256, the repository, commit and CI run that produced it, and the tool versions. The builder in `mesa-lab/evidence_pack` refuses:
- any input without a CI run reference;
- any decision record whose signature does not verify.

## What it does not claim

The pack shows how MESA artifacts support controls. It does not certify compliance. Planned artifacts (see the crosswalk status column) are listed as absent, not as met.
