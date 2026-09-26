# OWASP Top 10 for Agentic Applications (2026) crosswalk (draft v0)

Each row says what MESA covers, and what it does not.

| Risk | MESA coverage | Limit |
| --- | --- | --- |
| ASI01 Agent Goal Hijack | Bounds what a hijacked agent's composition can reach (INV01, frontier) | Does not detect the hijack itself |
| ASI02 Tool Misuse | Tool levels come from credentials, not descriptions (SC-08); frontier blocks closing calls at the PEP | Per-call intent judgement is J3, advisory only |
| ASI03 Identity & Privilege Abuse | AssumeRole merges, identity-mint edges, OBO edge caps (SC-09) | Needs IAM or Terraform inputs |
| ASI04 Agentic Supply Chain Vulnerabilities | Shared registries and caches as blackboard-capable surfaces (SC-01) | Does not scan package contents |
| ASI05 Unexpected Code Execution | Out of scope except where execution adds an edge observed by mesa-d | Sandboxing is out of scope |
| ASI06 Memory & Context Poisoning | Temporal closure over memory window W; only attested wipes reset (SC-03, SC-10) | Does not inspect memory content |
| ASI07 Insecure Inter-Agent Communication | goal-message and write edges between agents; GET-mutable external boards (SC-02) | Message authentication is out of scope |
| ASI08 Cascading Failures | Multi-hop closure and witness paths show how one agent's state reaches others | Availability failures are out of scope |
| ASI09 Human-Agent Trust Exploitation | HOLD-for-human verdicts carry witness and cut, not model text | Human judgement quality is out of scope |
| ASI10 Rogue Agents | Observer-independent drift (agent logs never trusted, SC-06) | Needs Tier 2 logs |
