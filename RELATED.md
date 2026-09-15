# Related works / citation links

## Paper ↔ software relationship

| Artifact | Role | Identifier |
|---|---|---|
| MESA paper | Primary scholarly work | DOI [10.5281/zenodo.22744547](https://doi.org/10.5281/zenodo.22744547) |
| mesa-ibi-scanner | Reference implementation of MESA-INV-01 | This repository (`v0.3.0`) |

When citing:

- The **paper** `isSupplementTo` relationship should point at this software once a **software DOI** exists.
- The **scanner** `isSupplementedBy` the paper DOI today: [10.5281/zenodo.22744547](https://doi.org/10.5281/zenodo.22744547).

Until a Zenodo software DOI is minted for this repo, do **not** invent a DOI number. See README for enablement steps (Zenodo–GitHub integration).

## Schema `$id` pins

- ACM: `schemas/v0.1/mesa-acm.schema.json` (pinned historically at `v0.2.0` tag URL)
- Topology: `schemas/v0.1/mesa-topology.schema.json` (pinned at `v0.3.0` tag URL)
