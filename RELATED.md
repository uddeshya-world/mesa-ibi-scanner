# Related works / citation links

## Paper ↔ software relationship

| Artifact | Role | Identifier |
|---|---|---|
| MESA paper | Primary scholarly work | DOI [10.5281/zenodo.22744547](https://doi.org/10.5281/zenodo.22744547) |
| mesa-ibi-scanner | Reference implementation of MESA-INV-01 | This repository (`v0.3.0`); **software DOI: pending Zenodo-GitHub enable** |

### Cross-link language (DataCite / Zenodo)

| From | Relation | To |
|---|---|---|
| Paper | **isSupplementedBy** | Scanner (GitHub URL today; **software DOI** once minted) |
| Scanner | **isSupplementTo** | Paper DOI `10.5281/zenodo.22744547` (see `.zenodo.json`) |

When citing:

- Cite the **paper** for the scholarly argument (preferred-citation in `CITATION.cff`).
- Cite the **software** (this repo / future software DOI) for the reference implementation.
- Do **not** reuse the paper DOI as if it were the software DOI.

Until a Zenodo software DOI is minted for this repo, keep the placeholder **pending Zenodo-GitHub enable**. Enablement steps: Zenodo → GitHub toggle for `uddeshya-world/mesa-ibi-scanner`, then a **new** tagged GitHub Release (existing `v0.3.0` is not auto-imported). See repo README and Zenodo’s GitHub enablement docs (https://help.zenodo.org/docs/github/enable-repository/).

## Schema `$id` pins

- ACM: `schemas/v0.1/mesa-acm.schema.json` (pinned historically at `v0.2.0` tag URL)
- Topology: `schemas/v0.1/mesa-topology.schema.json` (pinned at `v0.3.0` tag URL)
