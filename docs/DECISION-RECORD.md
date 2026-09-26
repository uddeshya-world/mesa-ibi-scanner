# Decision record specification

Status: draft for TASK-0016 (G-P3a). Owner approval pending. Schema: `schemas/v0.3-draft/mesa-decision-record.schema.json`. Fixture: `fixtures/runtime/decision-records.jsonl`, two records produced by mesa-pep.

An enforcement point emits one record per verdict (property P-16). An auditor should be able to read a record and answer: who asked for what, what the deterministic check said and why, whether any model changed it, and who signed it. Nothing in a record depends on a model to explain a verdict: Jev can block, it can never bless.

## Fields

| Field | Meaning |
| --- | --- |
| `record_id`, `time` | Unique id and RFC 3339 UTC time |
| `agent`, `principal_chain` | The acting agent, and the chain of principals it acts for |
| `obo_token_sha256` | Hash of the on-behalf-of token, never the token |
| `requested_edge` | Surface, flow type, direction (`inbound`, `outbound`) and any runtime levels |
| `state_before`, `state_after` | The agent's closure before, and as it would be after, the edge |
| `zone`, `threshold` | Zone and its threshold from the signed frontier |
| `frontier_version` | Content version of the frontier used; `null` when none was loaded |
| `deterministic_verdict`, `reason` | ALLOW, HOLD or BLOCK from the frontier lookup, with a machine reason (`closes-trifecta`, `obo-scope`, `undeclared-surface`, `agent-already-violating`, `no-frontier`, ...) |
| `witness`, `min_cut` | Filled when a scanner report is attached, otherwise `null` |
| `jev` | `null`, or the pinned model version, each question id with a SHA-256 of its wording, probability, threshold, margin, latency, and any failure |
| `final_verdict` | Never weaker than `deterministic_verdict` (P-09) |
| `reviewer_override` | `null`, or a human decision on a HOLD: reviewer, verdict, reason, time |
| `signature` | Ed25519 over the canonical JSON of every other field (sorted keys, compact separators) |

## Storage

Records go to an append-only store that agents cannot write to (AU-9, A-06): for example an object-locked bucket in a separate account. The enforcement point opens its local file append-only and exposes no route that writes or deletes records.

## Verification

1. Recompute the canonical bytes without `signature`.
2. Verify with the enforcement point's public key; `key_id` is the first 16 hex digits of the SHA-256 of the raw key.
3. Check that `frontier_version` names a frontier that was published and signed at that time.
