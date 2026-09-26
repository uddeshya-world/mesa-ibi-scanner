# ACM submission draft (agent proposal, not sent)

Status: **proposal**. A standards submission is text that leaves the repository, so the owner decides what is sent, to which body, and when (roadmap Sections 8 and 11). Candidate venues named in the roadmap: the OWASP GenAI Security Project and the OpenID Foundation.

## What is submitted

The Agent Composition Model (ACM): a typed description of agents, the surfaces they share, and the flows between them, sufficient to evaluate one invariant (INV-01). Nothing else from MESA is proposed as a standard.

| Artifact | Path | Version |
| --- | --- | --- |
| ACM document schema | `schemas/v0.1/mesa-acm.schema.json` | 0.1.0 |
| Topology schema, boolean | `schemas/v0.1/mesa-topology.schema.json` | 0.1.0 |
| Topology schema, graded | `schemas/v0.2/mesa-topology.schema.json` | 0.2.0 (after G7) |
| Timeline schema | `schemas/v0.2/mesa-timeline.schema.json` | 0.1.0 (after G10) |
| Reference evaluator | `mesa-ibi-scanner` | 0.4.0 |

## Scope statement (draft)

ACM lets any tool describe a multi-agent estate as vertices (agents and shared services) with graded Privilege, Untrusted-input and Egress levels, plus typed, capped edges. Any conforming evaluator computes the same closure and the same verdict per zone. ACM does not define detection of prompt injection, model behaviour, or enforcement mechanics.

## Questions the owner decides

1. Which body, and in which working group or project.
2. Whether to submit v0.1 (boolean, stable) or v0.2 (graded, after G7 and the FP report).
3. The licence terms for schema contributions.
4. Who is named as editor.

## Evidence to attach (after the gates pass)

- The G7 FP report against the G6 pre-registered target.
- The derivation-accuracy report against the G2 targets.
- The base-rate findings note (G9), including negative cases.
