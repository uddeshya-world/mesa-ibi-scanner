# Validation

Agents may write code and tests. They do not control the oracle that judges that work. This page summarises the ten rules and the roles from the MESA validation philosophy. `DECISIONS.md` holds framing text and is draft until the owner approves it.

The failure modes these rules exist to stop: editing or deleting a failing test, fixture, or expected output; loosening a threshold or zone until a number passes; special-casing a known fixture by name or hash; tests that only restate the implementation; a measurement that cannot be re-run; softened findings in papers and READMEs.

## Ten rules

1. **Oracle separation.** The agent that implements a change does not author or approve the tests that gate it. A separate test-author role writes tests from the spec. A human approves them.
2. **Spec before code.** Every task starts from a written spec with named acceptance checks. Those checks are merged before implementation starts.
3. **Protected paths.** Golden fixtures, expected outputs, thresholds, zone configs, schemas, gate definitions, and the claims ledger sit under CODEOWNERS (`.github/CODEOWNERS`). Changing them needs human approval and a written reason. In this repository the protected set also covers the harness itself: `tasks/`, `DECISIONS.md`, `.github/` (workflows, CODEOWNERS, harness scripts, the lint baseline), and `Makefile`.
4. **Holdout fixtures.** `mesa-holdout` holds fixtures and scenario variants that implementer agents never see. CI runs them. The log is pass or fail only. See `docs/HOLDOUT.md`.
5. **Pre-registration.** Metric definitions and pass thresholds are committed before the measurement run. A threshold changed after a run invalidates that run.
6. **Mutation testing.** Core modules must reach a mutation score target, so tests prove they can fail. Week 0 records `mutation_score` as null; the weekly mutation tier is not this milestone.
7. **Reproducibility.** Every reported number comes with the command, commit, seed, input dataset hash, and tool versions. CI re-runs it. `make evidence TASK=<id>` writes `evidence/<id>.json`. CI rebuilds that file and diffs it against the committed bytes.
8. **Property tests over examples.** Core behaviour is specified as properties checked on generated graphs, not only hand-picked cases. Week 0 runs the existing seeded property module. It does not yet run the later property catalogue at 10,000 cases; those properties depend on lattice, frontier, temporal, and enforcement work that is out of scope here.
9. **No network in tests.** Only the scenario lab talks to services, and only to lab infrastructure. T0 schema validation uses the schemas in this repo. The holdout job's clone is CI, not a unit test, and it runs only when the owner has configured the token.
10. **Human framing.** Abstracts, READMEs, claims, and the decision record are decided by a human. Agents propose. Humans choose. `DECISIONS.md` stays draft until the owner approves it.

## Roles

| Role | Does | Must not |
| --- | --- | --- |
| Implementer agent | Writes code to satisfy merged checks; produces the evidence bundle | Touch protected paths; read holdout content |
| Test-author agent | Writes property tests, fixtures and scenarios from the spec | Implement features in the same task |
| Reviewer agent | Checks diffs against the spec, the five design rules and this section; flags protected-path changes | Approve its own suggestions |
| Human owner | Approves specs, thresholds, fixtures, gates and all framing text | Waive a failing gate without writing the reason in the decision log |

## What `make verify` runs

| Target | Tier | What it runs today |
| --- | --- | --- |
| `make t0` | T0 static | Pinned ruff defect rules, a protected lint baseline, mypy, JSON Schema validation of example documents and built-in fixtures, Apache-2.0 licence check, secret scan, version consistency |
| `make t1` | T1 unit | `tests/test_topology.py`, `tests/test_topology_pdp_optional.py`, `tests/test_cli_output.py` |
| `make t2` | T2 property | `tests/test_properties.py` (fixed `random.Random` seeds) |
| `make t3` | T3 golden, public | `tests/test_closure.py` |
| `make t3-holdout` | T3 golden, holdout | `mesa-holdout`, or `holdout: not configured` (failure) |
| `make verify` | T0 then T1 then T2 then T3 | Stops on the first failure. Does not call holdout |

The 27 tests already in the tree are not modified by this harness. T1, T2, and T3 select disjoint files and together cover that set once.

T0 tools are pinned in `.github/harness/requirements-t0.txt`. Install them with the package before `make verify`:

```bash
pip install -e ".[dev]"
pip install -r .github/harness/requirements-t0.txt
```

## Gates and waivers

`gates/g0.yaml` lists the G0 machine checks and the human sign-off. A waiver can be added only by @uddeshya-world, in `DECISIONS.md`, with a date, a reason, and a follow-up date.
