# mesa-d design note (streaming drift detection)

Status: draft for TASK-0012 (G12). Owner approval pending. The roadmap's rule is "do not build drift detection before the Week 12 design note". mesa-d code starts only after this note merges, and only if the G7 false-positive kill criterion has not fired.

## 1. Purpose

The committed topology is policy. mesa-d watches what actually happens and raises three findings:

| Finding | Meaning |
| --- | --- |
| `UNDECLARED_EDGE` | An observed flow that the committed topology does not contain |
| `NEAR_MISS` | After the observed edge, an agent is short of its zone threshold on exactly one dimension |
| `INV01` | After the observed edge, an agent's closure meets its zone threshold |

mesa-d raises findings. It never blocks: blocking belongs to mesa-pep (design rule 1 applies to both).

## 2. Evidence sources (design rule 3)

Only sources that agents cannot write to are accepted. Each source is registered with a `source_id` and a trust class. Events from an unregistered source are dropped and counted.

| Source | Registered as | Yields |
| --- | --- | --- |
| AWS CloudTrail (organisation trail, delivered to a log-archive account) | `infra` | principal, action, resource |
| VPC Flow Logs | `infra` | src/dst address, port; joined to ENI owner |
| Egress proxy logs | `infra` | principal (from mTLS or workload identity), host, method, bytes |
| MCP gateway logs | `infra` | agent, server, tool, arguments hash |
| Kidon Shomer eBPF events, shipped off-host immediately | `infra` | process, syscall class, destination |
| Canary echoes | `infra` | canary id, external observer, time |
| Agent-reported tool logs | **rejected** | counted as `agent_log_ignored`; a disagreement with `infra` evidence is itself a finding (SC-06) |

## 3. Observed-edge event (ACM event format)

Every adapter normalises to one record:

```json
{
  "event_version": "0.1.0",
  "event_id": "sha256 of the raw record",
  "source_id": "cloudtrail-org",
  "observed_at": "2026-11-03T10:14:22.118Z",
  "received_at": "2026-11-03T10:14:23.004Z",
  "principal": "arn:aws:iam::111111111111:role/eval-c",
  "action": "s3:GetObject",
  "resource": "arn:aws:s3:::customer-records/2026/11/03.parquet",
  "raw_ref": "s3://log-archive/cloudtrail/...#offset"
}
```

## 4. Pipeline

1. **Ingest.** Per-source adapters read log files or streams and emit observed-edge events. There are no callbacks into agent infrastructure.
2. **Typed-edge resolver.** This is the derive action table (docs/DERIVATION.md section 5) applied to one event: principal to agent (via the committed topology's provenance), action to class, resource to service vertex, which gives `(src, dst, flow_type)`.
   - An unresolved principal or resource produces `UNDECLARED_EDGE` with confidence `requires-review`.
   - HTTP requests use GET-mutation detection (section 6), not the verb.
3. **Diff.** An edge not in the committed topology (ungated) produces `UNDECLARED_EDGE`. An edge that is present but gated produces `GATE_BYPASS` when the PEP decision log has no record for it.
4. **Incremental closure.** `mesa_ibi_scanner.lattice.IncrementalClosure.add_edge` on a working copy. Only the reverse cone of the destination is recomputed. Property P-06: after any event sequence, the streaming closure equals full recompute on the final graph.
5. **Temporal state.** Each agent's accumulated state follows docs/TEMPORAL.md over its window W. Only wipes attested by infrastructure events (pod or volume deletion, vector-store purge from `infra` sources) reset it (SC-10).
6. **Findings.** The first time an agent crosses into `NEAR_MISS` or `INV01`, mesa-d emits an OCSF-style Detection Finding with the witness path and minimal cut from the scanner, and dedups on `(agent, finding, frontier_version)`.

## 5. Output

- SARIF (the same rules as the scanner) for CI, per window.
- OCSF-style JSON (class Detection Finding) for SIEM: `finding_info.uid`, `finding_info.title`, `resources[]` (the agent and surfaces), `evidences[]` (event ids and raw refs), `unmapped.mesa` (closure, threshold, witness, min_cut, frontier_version).

## 6. GET-mutation detection and J2

- **Deterministic first.** A host counts as writable if any observed request to it by an agent carried a body, or used a state-changing method, or its egress-file entry lacks verification.
- **J2 (Jev):** called asynchronously on URL shape and response metadata. It may only **trigger active verification** in the lab (read, write canary, re-read). It never raises a finding by itself (roadmap Section 12). The adapter enforces this in code (P-09).

## 7. Canaries

Canaries are planted only on owned surfaces in the lab, one unique token per surface and principal. An echo observed at an external observer is attributed to the last principal that read the canary. The attribution rate is reported (SC-07).

## 8. Latency budgets

| ID | Budget |
| --- | --- |
| B-02 | Incremental update under 50 ms p99 per event |
| B-03 | Event arrival to finding under 1 s p99 (log delivery excluded) |

## 9. Failure modes

- **Source silent longer than its expected interval:** `SOURCE_GAP` finding. Silence never means no drift.
- **Committed topology unreadable or its signature invalid:** mesa-d stops emitting drift findings and raises `POLICY_UNAVAILABLE`.
- **Backpressure:** events are spooled to disk. Drops are counted and reported.

## 10. Test plan

- P-06 and P-08 properties on generated event streams.
- SC-01 to SC-11 replayed in shadow from recorded or synthetic logs in `mesa-lab`.
- B-02 and B-03 in CI.
- An agent-log spoofing fixture (SC-06): an agent-side log that disagrees with CloudTrail is ignored and reported.

## 11. Not in scope

Blocking; reading agent memory; any use of agent-reported logs as evidence; any model deciding a finding.
