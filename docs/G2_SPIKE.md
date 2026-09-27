# G2 derivation spike worksheet

Status: prepared for the owner. The owner does the timed runs. Agents do not fill in any result field.

## Purpose

Test two things about deriving a topology from Tier 0 artifacts by hand, following `docs/DERIVATION.md`:

1. The rules can be followed mechanically: few facts need a judgement the rules do not cover.
2. Derivation finds facts that authoring from memory misses, above all shared services.

Following rules by hand is nearly always slower than writing from memory, so time is recorded but is not the kill condition.

**Kill criterion (pre-registered, replaces the earlier time-based rule):** stop and rethink derivation (roadmap Section 14) if either holds:

- more than 20% of derived facts (vertices, edges and levels) needed a judgement call that no rule in `docs/DERIVATION.md` covers; or
- on the step-4 diff, the derived topology is less correct than the authored one (more differences resolved in the authored topology's favour).

The step-4 diff is the main result. Each shared service that derivation caught and authoring missed is evidence for MESA.

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
2. **Derivation run.** On a later day, start a timer. Read only the state file and IAM export. Apply `docs/DERIVATION.md` rule by rule and write `derived.json`, with a source pointer for each vertex, edge and level. Mark every fact that needed a judgement no rule covers. Stop the timer.
3. Validate both: `mesa-ibi-scan --input authored.json --format json` and the same for `derived.json`.
4. Diff the two topologies. For each difference, say which one is right and why.
5. List each fact you could not derive. Check it is in `docs/NEVER_DERIVABLE.md`, and add it there if it is missing.
6. Keep `derived.json` as the owner label set for this module. It is the first G5 held-out environment (`gates/g2.yaml`), so do not run `mesa-ibi-derive` on the module before this file is committed.

## Results (owner)

| Measure | Value |
| --- | --- |
| Authoring time (minutes) | |
| Derivation time (minutes) | |
| Vertices / edges authored | |
| Vertices / edges derived | |
| Facts not derivable | |
| Facts needing an uncovered judgement (count and % of derived facts) | |
| Diff differences resolved for derived / for authored | |
| Shared services caught by derivation and missed by authoring | |
| Kill criterion triggered (>20% uncovered judgements, or derived less correct) | |

## Sign-off

- [ ] Owner defends each finding in `derived.json` line by line (G2 human sign-off).
- [ ] T4 targets in `gates/g2.yaml` confirmed or replaced before any derive run.
