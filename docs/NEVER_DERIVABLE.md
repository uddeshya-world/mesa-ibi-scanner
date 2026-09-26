# Facts that cannot be derived

Status: draft for TASK-0002 (G2). Owner approval pending.

Derive cannot compute these facts from Tier 0 artifacts. Each one needs a human, or a later access tier. Derive emits a `requires-review` item with the conservative value until the fact is supplied.

| Fact | Why it cannot be derived | Who supplies it | Conservative default |
| --- | --- | --- | --- |
| Zone of each vertex (research, staging, production, regulated) | A business decision; account or tag names prove nothing (rule 4) | Owner of the estate | `production` |
| Which principals are agents | IAM does not say whether a role runs an agent, a human session or CI | ACM documents or `mesa-agents.yaml` | Not an agent vertex; still counted as a writer |
| MCP server to credential binding, when absent from config | MCP configs name commands and URLs, not the identity they run as | Platform engineer | `P=3, E=3` |
| Memory window W, when the ACM has no memory declaration | Durable memory depends on application code, not only on grants | Agent owner | `unbounded` |
| P level of an untagged data store | Content classification is not visible in IaC | Data owner, or DLP output | `3` |
| Whether an external domain mutates state on GET | Only an active test (read, write canary, re-read) or a human can tell | Reviewer, or J2 plus active verification in Phase 1 | Writable, `U=3` |
| Application-level PDP gates (human approval steps, policy checks inside code) | Not expressed in IAM or Terraform | Agent owner, cited in the overlay | No gate |
| Runtime-only reach: session policies, dynamic assume-role chains, credentials fetched at runtime | Resolved only at call time | Tier 2 logs (mesa-d) | Edge kept when any static grant allows it |
| SaaS integrations with their own OAuth grants (chat, ticketing, code hosting) | Outside the cloud account and usually outside IaC | Platform engineer | Listed as `ext:` surface, `U=3, E=3` |
| Cross-account trust beyond the exported accounts | The export covers only the accounts supplied | Owner, or a wider export | Foreign principal treated as external, `U=2` |
| Whether a flow is task-necessary | Intent, not configuration | Agent owner | Flow kept |
| Presence of injected content | A runtime property of data | Out of scope for derive | Not modelled |
| Any lowering of a derived level | Rule 2 and rule 4: only a human decision may lower | Reviewer, named in the overlay | Derived level stands |

Items in this table are counted in the T4 report under `T4-requires-review-share`.
