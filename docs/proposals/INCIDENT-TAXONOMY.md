# Incident-disclosure taxonomy proposal (agent draft)

Status: **proposal** for the owner (G12). It is for classifying disclosed multi-agent incidents consistently. It adds no MESA control.

## Fields

| Field | Values |
| --- | --- |
| `origin` | `own-agents`, `injected-content`, `external-attacker`, `unknown` |
| `surface_type` | `package-registry`, `message-queue`, `object-store`, `wiki-or-board`, `ticketing`, `memory-store`, `other` |
| `surface_mutation` | `write-api`, `state-changing-get`, `side-channel`, `unknown` |
| `trifecta_split` | For each of P, U and E: which agent or surface held it, or `not-reported` |
| `closure_reached` | `yes`, `no`, `partial` (name the dimension) |
| `evidence_source` | `infrastructure-logs`, `agent-logs`, `researcher-reconstruction`, `vendor-statement` |
| `agent_log_reliability` | `consistent`, `contradicted`, `spoofed`, `not-examined` |
| `in_mesa_scope` | `yes` or `no`, with reason (roadmap Section 1: external APT campaigns are out of scope) |

## Worked classification (from roadmap Section 2)

| Incident | origin | surface_type | surface_mutation | in_mesa_scope |
| --- | --- | --- | --- | --- |
| OpenAI / Hugging Face | own-agents | package-registry | write-api | yes |
| DseWiki | own-agents (attribution per researchers' evidence) | wiki-or-board | state-changing-get | yes |
| Tool-call spoofing | own-agents | other | unknown | yes (observer-independence lesson) |
| TeamT5 / Unit 42 reporting | external-attacker | not applicable | not applicable | no |

The corrections in `docs/proposals/WEEK1.md` apply before this table is used anywhere outside the repository.
