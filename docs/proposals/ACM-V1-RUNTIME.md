# ACM v1 runtime extensions (agent proposal)

Status: **proposal** for G-P3b. The owner decides whether and where to submit (roadmap Sections 8 and 11).

ACM v0.x describes a composition at design time. v1 would add two runtime records, so that any drift detector and any enforcement point can exchange evidence in one format.

| Extension | Schema (draft) | Producer | Consumer |
| --- | --- | --- | --- |
| Observed edge | `schemas/v0.3-draft/mesa-observed-edge.schema.json` | Infrastructure adapters (CloudTrail, proxy, MCP gateway, Kidon Shomer) | mesa-d or any drift detector |
| Decision record | `schemas/v0.3-draft/mesa-decision-record.schema.json` | Enforcement points (mesa-pep) | Auditors, SIEM |

## Rules that travel with the formats

- **Observer independence.** An observed-edge event is evidence only if its `source_id` is registered as infrastructure. Consumers recompute `event_id` on ingest; a producer-supplied id is not trusted.
- **Upward-only models.** A decision record's `final_verdict` is never weaker than its `deterministic_verdict`.
- **Signatures.** Frontiers and decision records are signed with Ed25519 over canonical JSON: sorted keys, compact separators, UTF-8.

## Open questions for the owner

1. Submit v1 together with, or after, the v0.2 graded topology?
2. Keep the `levels` vector at four levels in the standard, or leave the level scale to profiles?
3. Include `witness` and `min_cut` as required fields in decision records?
