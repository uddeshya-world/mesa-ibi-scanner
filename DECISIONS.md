# MESA decision record

Status: Approved by the owner, 27 Sep 2026 (in force from the owner's merge of this change)

Date: 25 Sep 2026

The text below is the Week 0 decision record, copied from the MESA Final Roadmap, Section 1 (25 Sep 2026). It is framing text, approved by the human owner.

## Decision

MESA is a standards-and-credibility play with open-source reference implementations. There is no commercial product before the Month 9 product gate. This plan runs 12 months, from Week 0.

## What MESA is

One computable check: Invariant 1 (INV-01) evaluated over a typed agent-composition graph. The public surface stays at four items: the Inventory of Blackboard Interactions (IBI), the Agent Composition Model (ACM), Anti-Consensus Authorization (ACA), and INV-01. Nothing is added to that surface in this plan.

## What MESA is not

- Not a jailbreak detector or behavioural judge of text.
- Not a defence against external APT campaigns; perimeter controls and patching cover that.
- Not a replacement for cloud-security graphs. It is a composition check that runs on top of them.

## Threat model MESA owns

Your own agents, or agents steered by injected content, completing the Privilege-Untrusted-Egress (P-U-E) trifecta across shared writable surfaces. No single agent holds all three; the composition does.

## Why not a product yet

- Cloud-security platform vendors already own the graph, the read access and the buyer. MESA's leverage is its semantics, adopted into their graphs.
- There is no base-rate number or measured false-positive rate yet. Selling now means selling a claim.

## Month 9 product gate

Revisit a product only if all three hold:

1. At least three organisations have run `mesa-ibi-derive` on their own estates without your help.
2. The base-rate study shows blackboard-capable services are common, not rare.
3. No major platform vendor has shipped an equivalent composition check.

## Five design rules

Every milestone, test and pull request is judged against these.

1. **Deterministic authority.** Only graph computation decides ALLOW. Nothing probabilistic can permit an action.
2. **Upward-only models.** Jev, or any model, may raise a lattice level, BLOCK or HOLD. It may never lower a level or ALLOW.
3. **Observer independence.** Runtime evidence comes only from sources agents cannot write to. Agent-reported tool logs are never trusted.
4. **Derived, not asserted.** Every property level traces to a grant, a policy or a human decision. Resource names prove nothing.
5. **Over-inclusion beats omission.** A spurious edge is a review item. A silently missed shared service is a release blocker.

## Starting state (v0.3.2)

| Item | State |
| --- | --- |
| Paper | Zenodo preprint, concept DOI 10.5281/zenodo.22743175 |
| Scanner | mesa-ibi-scanner v0.3.2: cut semantics, flow masks, topology input, SARIF, CI, 27 tests green |
| Schema | ACM JSON Schema and topology schema v0.1 (boolean P/U/E) |
| Input | Hand-authored topology JSON |
| Gaps | Derivation, graded lattice, temporal closure, runtime drift, enforcement point |

## Disclosure decision: base-rate study (G8, G9)

Decided by the owner on 30 Sep 2026, before the sample is drawn. It is fixed together with the other base-rate pre-registration (`prereg/`) and is not changed after results exist. A later change applies only to a new run.

**What the study observes.** Public Terraform code at a pinned commit, read offline. derive parses HCL with no provider calls, no credentials, no state files, and no contact with any deployed system. A blackboard-capable service in public infrastructure code is a *capability* (docs/BASERATE.md section 6). It is not evidence of a deployed agent estate, and not by itself a vulnerability.

**Publication.**

1. Papers, the findings note, talks, posts and the README report **aggregates only**: BR-1 to BR-5 with intervals, exclusion and parse-failure counts, and negative cases by count and shape.
2. No publication names, links, ranks or quotes a sampled repository as having a finding. Worked examples are rebuilt as synthetic topologies with identifiers changed. They are never excerpts of a sampled repository.
3. **Amended 3 Oct 2026 by the owner, before the sample was drawn (option 3, mesa-ops #2).** No published artifact pairs a repository, or a sample position, with its result. The published dataset holds:
   - the reproducibility inputs: the query, the frame, the seed and the sampling and runner code;
   - the aggregates in point 1;
   - one SHA-256 per included or excluded row, computed over the row's **complete** canonical record (repository, path, commit, inclusion decision and every derived field, witness paths included), listed in sorted hash order with no ids or fields beside it.

   `corpus/manifest.json` and per-row results (`results.json`, `exclusions.md`) are owner-held and never committed to a public repository. A reproducer re-draws the sample from the frame and seed with `corpus/sample.py`, runs `make reproduce-baserate`, and checks that the dataset SHA-256 and the set of row hashes match. Hashing the full record means a row hash can only be matched by re-running derivation on that repository, not by guessing a verdict. This supersedes the sentence in `docs/BASERATE.md` section 8 about publishing the manifest; that file is left unchanged because its hash is pre-registered. The dataset README says that results show capability in example and template code, not insecurity of a deployed system.
4. Rows for repositories whose licence forbids redistribution of derived data are published without paths (docs/BASERATE.md section 4).

**No contact during the study.** Nobody working on MESA, human or agent, opens issues, pull requests, discussions or messages on a sampled repository, or contacts its owners, while sampling and analysis are under way. Contact could change the population being measured. Agents never contact third parties about the study at any time.

**When private disclosure applies.** It applies only when the owner, reviewing exclusions or negative cases, finds **both** of the following:

- a live credential or secret committed in the sampled code, or
- clear evidence that the code describes a deployed production estate where agents run, and the derived P-U-E composition is complete there.

A blackboard-capable service in example or template code does not qualify. In a qualifying case:

1. The owner, not an agent, reports it privately: through GitHub private vulnerability reporting, the repository's `SECURITY.md` contact, or the owner's listed contact, in that order.
2. The report gives only what is needed to fix the problem. A committed credential is described by file and line, never copied into MESA's data, logs or issues.
3. The embargo is 90 days from the report, or until a fix, whichever is sooner. The case is never named publicly, even after the embargo, unless its owner agrees in writing.
4. The environment stays in the sample, so the statistics don't change. Its row is published without a path, and the number of such cases is reported as a count.
5. A committed credential is never used, tested or validated.

**Removal on request.** A repository owner can ask for their row to be removed from the published dataset. Published numbers keep their dataset hash. A later dataset version replaces the row's identifiers with `withheld`, and removals are reported as a count.

**Clones.** Sampled repositories are cloned only into the local run cache (`.cache/corpus`). They are not redistributed, and the cache is deleted after results are published. Only ids, commits and derived counts are kept.

This decision does not cover disclosures about MESA's own incident taxonomy (G12). That proposal is separate.

## Waivers

A gate can be waived only by the human owner, @uddeshya-world. Agents cannot create waivers.

Each waiver added to this file must include all three of the following:

- the date of the waiver
- the reason
- the follow-up date

No waivers are recorded.
