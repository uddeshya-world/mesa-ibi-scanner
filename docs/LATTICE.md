# Graded lattice specification

Status: draft for TASK-0006 (G6). Owner approval pending. Zone thresholds and the false-positive metric are **pre-registered** in `thresholds/zones.json` and `gates/g6.yaml` before any measurement.

The boolean model (v0.1) sets one bit per dimension. It flags every agent whose closure touches any private data, any untrusted input and any egress, however weak. The graded lattice keeps the same closure rule and replaces each bit with a level.

## 1. Levels

Each vertex carries a level vector `L = (P, U, E)`, each component in `{0, 1, 2, 3}`.

| Dimension | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| P (privilege) | none | synthetic/test | internal | regulated/customer |
| U (untrusted input) | none | authenticated-internal | anonymous-external | public-writable |
| E (egress) | none | mesh-internal | allowlisted-external | open-internet |

## 2. Join

`join(a, b) = (max(a.P, b.P), max(a.U, b.U), max(a.E, b.E))`. Join is commutative, associative and idempotent, and `(0, 0, 0)` is its identity (property P-02). Levels form a join-semilattice: the product of three 4-element chains.

## 3. Flow caps (mask attenuation)

A flow mask no longer clears bits. Each flow type has a **cap** vector, and a level crossing an edge is limited component-wise to that cap:

`attenuate(L, cap) = (min(L.P, cap.P), min(L.U, cap.U), min(L.E, cap.E))`

| Flow type | Cap (P, U, E) | v0.1 mask |
| --- | --- | --- |
| write | (3, 3, 3) | (1, 1, 1) |
| read | (3, 3, 0) | (1, 1, 0) |
| goal-message | (0, 3, 0) | (0, 1, 0) |
| proxy/egress | (0, 0, 3) | (0, 0, 1) |
| identity-mint | (3, 0, 3) | (1, 0, 1) |

Each cap is its v0.1 mask with 1 promoted to 3. An edge may also carry an explicit `cap` in schema v0.2, for example a scoped on-behalf-of token (scenario SC-09). The effective cap is the component-wise minimum of the flow cap and the edge cap. Attenuation never raises a level (property P-03).

An unknown flow type gets cap (3, 3, 3). This is the over-inclusion rule.

## 4. Closure

On the residual graph (every edge with `pdp_gate: true` removed; cut semantics as in v0.2.0), the closure is the least fixpoint of

`Cl(v) = L(v) ⊔ ⊔ { attenuate(Cl(u), cap(e)) : e = u → v }`.

Adding an edge never lowers any closure (P-01). Nothing crosses a gated edge (P-04).

Per dimension, `Cl_d(v)` equals the maximum over all sources `u` of `min(L_d(u), bottleneck_d(u → v))`, where `bottleneck_d` is the widest-path value of the `d` components of the caps. The frontier (section 7) uses this.

## 5. Zones and violation

Each agent has a zone: `research`, `staging`, `production` or `regulated`. A missing zone is `production` (docs/NEVER_DERIVABLE.md). Each zone has a threshold vector `T_z`.

**INV01:** agent `a` in zone `z` violates when `Cl(a) ≥ T_z` component-wise, that is `Cl_P(a) ≥ T_z.P` and `Cl_U(a) ≥ T_z.U` and `Cl_E(a) ≥ T_z.E`.

**NEAR_MISS:** exactly one component is below the threshold. The finding names that component.

The thresholds live in `thresholds/zones.json`, a protected path. Input topologies cannot override them, because an input that sets its own thresholds could make any finding disappear.

Proposed thresholds (the owner approves or replaces them):

| Zone | T.P | T.U | T.E | Meaning |
| --- | --- | --- | --- | --- |
| research | 3 | 3 | 3 | Only regulated data, public-writable input and open internet together |
| staging | 2 | 2 | 3 | Internal data, anonymous input, open internet |
| production | 2 | 2 | 2 | Internal data, anonymous input, allowlisted external egress |
| regulated | 1 | 1 | 1 | Any of each; same verdicts as the boolean model |

## 6. Boolean migration map (v0.1 to v0.2)

A v0.1 document is promoted automatically:

| v0.1 | v0.2 |
| --- | --- |
| `w[d] = 0` | level 0 |
| `w[d] = 1` | level 3 |
| flow mask bit 1 / 0 | cap 3 / 0 (the table in section 3) |
| no zone | `production` |
| no memory window | `1` (stateless) |
| `pdp_gate` | unchanged |

**Why the verdicts match (P-05).** After promotion every level is 0 or 3 and every cap is 0 or 3. The closure is then exactly 3 × the boolean closure, component by component. A promoted agent meets any threshold with components in 1 to 3 if and only if its boolean closure is (1, 1, 1). So every v0.1 fixture keeps its verdict under every zone threshold proposed above, production included.

## 7. Closure frontier

For each agent `a`, the frontier lists the candidate edges incident to `a` whose addition to the residual graph would create a violation that is not there without them.

- **Inbound** `(s → a, flow f)`: the new contribution into `a` is `attenuate(Cl(s), cap(f))`.
- **Outbound** `(a → s, flow f)`: the new contribution into `s` is `attenuate(Cl(a), cap(f))`. It can push a downstream agent past its threshold, not only `a`.

The check needs no graph traversal per call. For each vertex `v`, precompute the minimal **requirement vectors** `R(v)`. `r ∈ R(v)` means: a contribution `c` into `v` with `c ≥ r` component-wise makes some agent `x` downstream of `v` newly violate. For `x` with closure `Cl(x)` and threshold `T`:

`r_d = T_d if Cl_d(x) < T_d else 0`, feasible only if `bottleneck_d(v → x) ≥ r_d`.

A candidate edge is in the frontier if and only if its contribution meets some requirement vector at its destination (property P-07). The exported frontier holds, per agent:

- `inbound`: the list of `(surface, flow_type)` pairs in the frontier,
- `outbound`: the same for writes,
- `requirements`: `R(a)` itself, so an enforcement point can check a contribution whose levels were raised at runtime,
- `violating_now`: whether the agent already violates. An enforcement point holds every call from such an agent in production and regulated zones.

The frontier document has a content-derived `frontier_version` and an optional Ed25519 signature over its canonical JSON bytes. It is deterministic: the same topology and thresholds give byte-identical output (P-10).

## 8. Witness paths and minimal cuts

For a violating agent `x`, each dimension `d` has a **witness path**: a path from a vertex `u` with `L_d(u) ≥ Cl_d(x)` to `x` whose caps are all at least `Cl_d(x)` in component `d`. Joining the witnesses reproduces the reported closure (P-11). Paths are shortest, with ties broken by vertex id.

The **minimal cut** is a smallest set of ungated edges whose removal breaks the violation. Breaking it needs one dimension `d` to fall below `T_d`. For each `d` where `x`'s own level is below `T_d`, compute the minimum edge cut between the sources `{u : L_d(u) ≥ T_d}` and `x`, in the graph of edges with cap `≥ T_d` in component `d`. The reported cut is the smallest of those, ties broken by dimension order P, U, E. No proper subset of it breaks the violation (P-12). If `x`'s own levels already meet the threshold, no edge cut exists and the finding says so.

## 9. What the lattice does not change

Cut semantics, the fixpoint rule and the four-item public surface (IBI, ACM, ACA, INV-01) are unchanged. The v0.1 CLI output for v0.1 input is unchanged unless `--lattice` is passed.
