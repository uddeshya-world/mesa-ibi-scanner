# Temporal closure

Status: draft for TASK-0008 (G10). Owner approval of the formal definition pending. Behind a flag: `mesa-ibi-scan --timeline TIMELINE.json`.

Static closure evaluates one snapshot of the estate. An agent with memory can hold private data it read at time 1 and use an egress path it gained at time 2, even though no single snapshot shows both. Temporal closure carries each agent's accumulated state across snapshots, for as long as its memory lasts.

## 1. Input

A timeline is an ordered list of steps `t = 1..n`. Each step has:

- `topology`: a v0.1 or v0.2 topology document (the snapshot at that step);
- `sessions` (optional): map from agent id to session id at that step;
- `wipes` (optional): memory wipes before this step, each `{agent, attested, source}`.

A wipe is **attested** only when infrastructure observed it: for example a pod or volume deletion, or a vector-store purge in a log the agent cannot write. An agent's own claim is recorded with `attested: false`. It does not reset anything (design rule 3).

## 2. Memory window

Each agent's window `W` comes from `memory_window` on its vertex in the current snapshot: `1`, `session` or `unbounded` (default `1`). A v0.1 snapshot has `W = 1`.

## 3. Definition

Let `S_t` be the snapshot at step `t`, `L_t(a)` the agent's own levels in it, and `Cl_t` the closure of the effective graph defined below. The memory carried into step `t` is

- `W = 1`: `M_t(a) = (0, 0, 0)`;
- `W = session`: `M_t(a) = ⊔ { Cl_s(a) : r ≤ s < t }`, where `r` is the first step of the current run of steps with the same session id as step `t`;
- `W = unbounded`: `M_t(a) = ⊔ { Cl_s(a) : r ≤ s < t }`, where `r` is the step after the latest attested wipe of `a` at or before `t` (or 1).

An attested wipe at step `t` also starts a new run for `W = session`.

The **effective graph** at step `t` is `S_t` with every agent's own levels replaced by `L_t(a) ⊔ M_t(a)`. What an agent remembers flows onward through what it writes. `Cl_t` is the lattice closure (docs/LATTICE.md) of the effective graph. INV01 and NEAR_MISS at step `t` use the agent's zone in `S_t`.

## 4. Properties (P-08)

- `W = 1` for every agent gives exactly the static result at every step.
- `W = unbounded` gives a closure at least the static closure, component-wise, at every step.
- After an attested wipe at step `t`, the result at step `t` and later equals the result of the timeline that starts at `t`.
- An unattested wipe changes nothing.

## 5. Scenarios

- **SC-03:** P granted at step 1, E at step 2, durable memory. Static passes at both steps; temporal INV01 at step 2.
- **SC-10:** memory wipe claimed by the agent but not observed. State is not reset, so the NEAR_MISS persists.
