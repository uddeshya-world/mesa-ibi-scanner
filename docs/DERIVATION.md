# Derivation mapping specification

Status: draft for TASK-0002 (G2). Owner approval pending.

This page defines how `mesa-ibi-derive` turns artifacts a customer already has (access Tier 0) into a topology the scanner can evaluate. Derive output is a **draft**. A human reviews it and commits it as policy.

Two design rules drive every mapping below:

- **Derived, not asserted (rule 4).** Every vertex, edge and level points to the grant, policy, tag or human decision it came from. A resource name proves nothing.
- **Over-inclusion beats omission (rule 5).** When a mapping cannot be resolved, derive emits the edge or the higher level and marks it `requires-review`. It never drops the fact to avoid noise.

## 1. Inputs (Tier 0)

| Input | Expected form | Flag |
| --- | --- | --- |
| Terraform state or plan | `terraform show -json` output of a state (`values.root_module`) or of a plan file (`planned_values.root_module` with `configuration`); child modules walked | `--tfstate` (`tfstate.json` or `tfplan.json` in `--dir`) |
| IAM authorization export | `aws iam get-account-authorization-details` JSON | `--iam` |
| Cartography or PMapper export | Edge list JSON (principal, action, resource) | `--graph-import` |
| MCP configuration | `mcpServers` map as used by MCP clients, plus an optional credential binding | `--mcp` |
| Egress allowlist | Plain list of domains, or YAML with `domains:` and optional `method_safe:` per domain | `--egress` |
| Agent declarations | `mesa-agents.yaml`: principals per agent (role ARNs, or `tf:<address>` when the ARN is unknown at plan time), MCP servers and bindings, zone, memory window. Reading ACM documents directly is **not implemented** yet | `--agents` |
| Human overlay | `overlay.yaml` of reviewed corrections (section 8) | `--overlay` |

Derive makes no network calls. It reads files on the machine where it runs.

### 1.1 IAM declared in Terraform

Public modules have no IAM export. Derive also reads grants from Terraform: `aws_iam_role` (including `inline_policy` blocks), `aws_iam_role_policy`, `aws_iam_policy`, `aws_iam_role_policy_attachment`, and `data.aws_iam_policy_document`. These are merged with an IAM export when both are present. Pointers: `tfstate:<address>#policy#Statement[<i>]`, `tfstate:<address>#inline_policy[<j>]#Statement[<i>]`.

### 1.2 Plan JSON and unknown values

In a plan, ARNs and rendered policies are often unknown. Derive resolves them through `configuration` references:

- A policy document statement whose `resources` reference a resource becomes a `tfref:<address>` resource. It matches the service with that Terraform address, with confidence `inferred`. Pointer: `tfconfig:<document address>#statement[<i>]`. References to `var.` or `local.` that cannot be resolved become `*` (over-inclusion).
- A compute resource's role (`role`, `task_role_arn`) is resolved from its reference when the ARN is unknown.
- A service whose ARN is unknown gets a synthetic ARN with wildcard region and account (for example `arn:aws:sqs:*:*:jobs`). A statement naming the concrete ARN matches it, with confidence `inferred`.
- A role whose name is unknown is keyed `tf:<address>`. `mesa-agents.yaml` may name principals that way.

### 1.3 Output versions

`--topology-version 0.1.0` (default) writes boolean `w`. `0.2.0` writes graded levels, zone and memory window (docs/LATTICE.md, docs/TEMPORAL.md). A missing zone becomes `production` and a missing memory declaration becomes `unbounded`, each with a review item (docs/NEVER_DERIVABLE.md).

## 2. Confidence classes

| Class | Meaning | Example |
| --- | --- | --- |
| `derived` | Follows from an explicit grant or policy with fully resolved principal, action and resource | Role `agent-a` has `s3:PutObject` on `arn:aws:s3:::cache/*` |
| `inferred` | Follows from a documented default rule or a resolvable wildcard expansion | `s3:*` expanded through the action table; security group `0.0.0.0/0` egress with a NAT route |
| `requires-review` | Cannot be resolved from the inputs; emitted anyway at the conservative value | `Resource: "*"`; a data store without a classification tag; an allowlisted domain with unknown GET behaviour |

A human decision in the overlay has class `human` and names the reviewer.

## 3. Identity and vertex ids

- Agent vertex: `agent:<name>`, where `<name>` is the ACM `agent_id` or the `mesa-agents.yaml` key. An agent binds to one or more IAM principals (role ARNs) and optionally to MCP servers.
- Service vertex: `svc:<type>:<name>`, where `<type>` is the AWS service prefix (`s3`, `sqs`, `sns`, `dynamodb`, `codeartifact`, `ecr`, `secretsmanager`, `ssm`, `lambda`, `kinesis`, `efs`) and `<name>` is the resource name taken from the ARN.
- External surface: `ext:<domain>` for each allowlisted domain.
- Principals that no agent binds to (humans, CI roles) are **not** vertices. Their grants still count as writers when derive decides whether a service is blackboard-capable, and they are listed in the review report.

## 4. Vertices

A resource becomes a service vertex when either of these holds:

1. It carries a resource policy (`aws_s3_bucket_policy`, `aws_sqs_queue_policy`, `aws_sns_topic_policy`, `aws_ecr_repository_policy`, `aws_codeartifact_repository_permissions_policy`, `aws_secretsmanager_secret_policy`, `aws_lambda_permission`).
2. At least one agent principal holds a classified action on it (section 5).

**Blackboard-capable.** A service is tagged `blackboard-capable` when it has at least two distinct writer principals (agent or not) and at least one reader principal. The tag is an inventory label for the IBI. It does not change closure: the edges exist whether or not the tag is set.

A service with exactly one writer and one reader that is a different principal is tagged `channel` and listed in the review report.

## 5. Edges from IAM

For each agent principal, derive collects the effective allow set:

- identity policies (inline, attached managed, group), then
- resource policies that name the principal, then
- explicit `Deny` statements removed when they resolve fully. An unresolvable `Deny` (conditions, `NotResource`) does **not** remove the edge. The edge stays and is marked `requires-review`.

Each action is classified with the action table below. Anything not in the table is ignored and counted in the review report as `unclassified-action`.

| Class | Actions (non-exhaustive, full table ships with derive) | Edge |
| --- | --- | --- |
| write | `s3:PutObject`, `sqs:SendMessage`, `sns:Publish`, `dynamodb:PutItem`, `dynamodb:UpdateItem`, `codeartifact:PublishPackageVersion`, `ecr:PutImage`, `kinesis:PutRecord`, `ssm:PutParameter`, `secretsmanager:PutSecretValue`, `elasticfilesystem:ClientWrite` | `agent -> svc` flow `write` |
| read | `s3:GetObject`, `sqs:ReceiveMessage`, `dynamodb:GetItem`, `dynamodb:Query`, `dynamodb:Scan`, `codeartifact:ReadFromRepository`, `ecr:BatchGetImage`, `kinesis:GetRecords`, `elasticfilesystem:ClientMount` | `svc -> agent` flow `read` |
| secret-read | `secretsmanager:GetSecretValue`, `ssm:GetParameter`, `ssm:GetParameters`, `kms:Decrypt` | `svc -> agent` flow `read`, sets P on the store (section 6) |
| invoke | `lambda:InvokeFunction`, `states:StartExecution` | `agent -> svc` flow `goal-message` |
| identity | `sts:AssumeRole`, `iam:PassRole`, `iam:CreateAccessKey` | `agent -> target` flow `identity-mint` |

Rules:

- `service:*` and `*` actions expand through the table. The resulting edges are `inferred`.
- A resource ARN with a wildcard that matches known resources expands to each match (`inferred`).
- `Resource: "*"` (or a pattern matching no known resource) yields an edge to **every** service vertex of that service type, each `requires-review`. This is the over-inclusion rule; the review report groups these by statement so one correction covers them.
- `sts:AssumeRole` into another agent's role merges that role's grants into the caller as `inferred` edges, one hop, with the source chain recorded.

## 6. Levels

v0.1 topology carries boolean `w`. Derive computes a graded level 0-3 per dimension (roadmap Section 3) and writes `w[d] = 1` if the level is at least 1. The graded levels go to `facts.json` now and into topology v0.2 at G7.

**P (privilege), on data stores.**

| Evidence | Level | Confidence |
| --- | --- | --- |
| Tag `mesa:classification` or `data-classification` = `regulated`, `pii`, `pci`, `phi`, `customer` | 3 | derived |
| Tag = `internal` or `confidential` | 2 | derived |
| Tag = `synthetic` or `test` | 1 | derived |
| Tag = `public` | 0 | derived |
| Secrets Manager secret, SSM SecureString, or KMS key with no tag | 3 | inferred |
| Any other data store with no tag | 3 | requires-review |

A missing tag never produces a lower guess. The reviewer may lower it in the overlay; that is a human decision (rule 4) and is recorded.

**U (untrusted input), on services.**

| Evidence | Level | Confidence |
| --- | --- | --- |
| Resource policy allows a write-class action to `Principal: "*"` with no restricting condition | 3 | derived |
| Public ingress into the service: API Gateway (v1 method or v2 route) with authorization `NONE` integrated with the service, or a Lambda function URL with `authorization_type = NONE` | 2 | derived |
| Write-class access from another account | 2 | derived |
| Two or more distinct writer principals in-account | 1 | derived |
| One writer | 0 | derived |
| External surface `ext:<domain>` with no `method_safe: true` in the egress file | 3 | requires-review |

**E (egress), on agents.**

| Evidence | Level | Confidence |
| --- | --- | --- |
| Agent compute has a security group egress rule to `0.0.0.0/0` or `::/0` on any port, and the subnet routes to an internet or NAT gateway | 3 | inferred |
| Egress limited to an allowlist proxy or Network Firewall domain list | 2 | derived |
| Egress only to VPC endpoints or in-VPC CIDRs | 1 | derived |
| No egress path | 0 | derived |
| Agent compute not found in state | 3 | requires-review |

**MCP servers.** An MCP server used by an agent acts with its own credentials. Derive takes the server's edges from what those credentials can reach (sections 5 and 6) and attributes them to the using agent, with the server named in provenance. The server is assumed to run beside the agent, so its egress is the agent's egress. A tool description such as "read-only" is a hint. If it disagrees with the credentials, derive keeps the credential-derived edges and adds a `description-mismatch` review item (scenario SC-08).

An MCP server whose credentials are not bound in config or `mesa-agents.yaml` gets `P=3, E=3` with `requires-review`.

## 7. Egress and GET-mutable surfaces

Every allowlisted domain becomes `ext:<domain>` with:

- an edge `agent -> ext:<domain>` flow `proxy/egress` for each agent whose egress passes the allowlist, and
- an edge `ext:<domain> -> agent` flow `read`.

A domain is a **writable surface** unless the egress file marks it `method_safe: true`, and that mark must cite an active verification (read, write canary, re-read) or a human decision. A GET-only allowlist does not make a domain read-only: the DseWiki case showed a site that changed state on GET. Unverified domains therefore get `U=3`, `requires-review`, and the flag `get-mutable-unverified`.

## 8. Provenance and the overlay

Every emitted fact carries:

```json
{"fact": "edge", "src": "agent:a", "dst": "svc:s3:cache", "flow_type": "write",
 "confidence": "derived",
 "source": "iam:role/agent-a#policy/cache-rw#Statement[0]"}
```

Source pointer forms: `iam:<principal-type>/<name>#policy/<name>#Statement[<i>]`, `tfstate:<address>#<attribute>`, `mcp:<server>#<field>`, `egress:domains[<i>]`, `rule:<name>` for a documented default, `overlay:<id>`. Pointers never contain file-system paths, so output does not depend on where the inputs live.

The overlay is a list of corrections keyed by fact identity (`fact`, `src`, `dst`, `flow_type` for edges; `vertex`, `dimension` for levels). Each correction names a reviewer and a reason. On regeneration:

- A correction whose fact still exists is re-applied.
- A correction whose source fact disappeared is **not** applied and becomes a review item `overlay-orphan` (property P-14).
- A correction that lowers a level or removes an edge is allowed only with a reviewer name. Derive never lowers a level on its own.

## 9. Outputs

| File | Content |
| --- | --- |
| `topology.json` | Schema v0.1 topology. Validates and scans with `mesa-ibi-scan --input` |
| `facts.json` | Every fact with graded level, confidence and source |
| `review.md` | Grouped review items: requires-review facts, orphans, mismatches, unclassified actions, non-agent writers |

`derive diff old/ new/` compares two runs by fact identity and prints added, removed and changed facts.

Output ordering is sorted by id, so the same inputs give byte-identical files (P-10).
