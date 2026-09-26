# G2 derivation spike worksheet

Status: prepared for the owner. The owner does the timed runs. Agents do not fill in the time fields; they feed a Section 14 kill criterion.

## Purpose

Show that deriving a topology from Tier 0 artifacts by hand, following `docs/DERIVATION.md`, is faster than authoring the topology from knowledge of the estate. If it is slower, stop and rethink derivation (roadmap Section 14).

## Inputs

Use one public Terraform module that deploys more than one workload principal and at least one shared data service, plus its IAM set. Record which one:

| Field | Value |
| --- | --- |
| Module (URL and commit) | |
| Terraform version | |
| How state was produced (`terraform plan -out` + `show -json`, or applied in a sandbox) | |
| IAM export source | |

`mesa-ibi-derive` ships reference environments under `reference/` that can serve as a second input. They are synthetic, so they do not replace the public module for this spike.

## Procedure

1. **Authoring run.** Start a timer. Write `authored.json` (topology v0.1) from your understanding of the module, without reading the state file. Stop the timer.
2. **Derivation run.** On a later day, start a timer. Read only the state file and IAM export. Apply `docs/DERIVATION.md` rule by rule and write `derived.json`, with a source pointer for each vertex, edge and level. Stop the timer.
3. Validate both: `mesa-ibi-scan --input authored.json --format json` and the same for `derived.json`.
4. Diff the two topologies. For each difference, say which one is right and why.
5. List each fact you could not derive. Check it is in `docs/NEVER_DERIVABLE.md`, and add it there if it is missing.

## Results (owner)

| Measure | Value |
| --- | --- |
| Authoring time (minutes) | |
| Derivation time (minutes) | |
| Vertices / edges authored | |
| Vertices / edges derived | |
| Facts not derivable | |
| Kill criterion triggered (derivation slower than authoring) | |

## Sign-off

- [ ] Owner defends each finding in `derived.json` line by line (G2 human sign-off).
- [ ] T4 targets in `gates/g2.yaml` confirmed or replaced before any derive run.
