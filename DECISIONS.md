# MESA decision record

Status: DRAFT pending owner approval

Date: 25 Sep 2026

The text below is the Week 0 decision record, copied from the MESA Final Roadmap, Section 1 (25 Sep 2026). It is framing text. It is not in force until the human owner approves it.

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
- Founder attention is already committed to Uroniyx.

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

## Waivers

A gate can be waived only by the human owner, @uddeshya-world. Agents cannot create waivers.

Each waiver added to this file must include all three of the following:

- the date of the waiver
- the reason
- the follow-up date

No waivers are recorded.
