# Holdout fixtures

`mesa-holdout` is a private repository. The human owner creates it. Implementer agents do not get a checkout, a token, or fixture contents.

The authoritative result is a commit status named `holdout` on the pull request head. The log prints one line and nothing else:

- `holdout: pass`
- `holdout: fail`
- `holdout: not configured` when the environment secret is unset or blank

`holdout: not configured` fails the job. An empty corpus, a failed clone, a schema or load error, or a result mismatch also fails the job. None of those cases print fixture names, file contents, paths, or diffs. The workflow uploads no artifacts.

Pull-request CI does not run this check and does not receive the token. Its `t3-holdout` job only prints `holdout: runs in holdout.yml (owner-dispatched)` and exits 0. `make t3-holdout` still runs `holdout.py` locally and fails closed when the token is absent.

## Who runs it

The owner decides when to run the holdout. Each run reveals one bit (pass or fail) about the private fixtures, so repeated dispatches can be used to probe the corpus. Run it when a result is needed, not on every push from an agent.

Dispatch `.github/workflows/holdout.yml` from `main` with the pull request number. The job uses the `holdout` environment. On a push to `main` the same workflow runs against that commit. Both checkouts set `persist-credentials: false`.

The workflow keeps trusted and candidate code apart:

1. Check out `main` into `trusted/`. The clone command and the comparator run only from here.
2. Check out `refs/pull/<n>/head` into `candidate/`.
3. Build a candidate wheel in a step whose environment has no holdout secret.
4. Clone `mesa-holdout` into `$RUNNER_TEMP/holdout`. This is the only step with `MESA_HOLDOUT_TOKEN` set, and it runs trusted code only.
5. Run the installed candidate inside `docker run --network none --read-only`. Only `fixtures/` is mounted, read-only. The candidate's stdout and stderr go to `/dev/null`. JSON reports go to a temp directory. `expected/` is not mounted.
6. `trusted/.github/harness/holdout.py compare` prints the one line above.
7. Post commit status `holdout` on the pull request head SHA. The description is that same line.

The container image is pulled and built on the host. The running container has no network.

## Layout the owner commits

```text
fixtures/**/*.json
expected/<same relative path>.json
```

Every `*.json` file under `fixtures/` is a topology document. This repo validates it with the local schema `schemas/v0.1/mesa-topology.schema.json`. That check does not fetch the schema `$id`.

The matching file under `expected/` is a scanner JSON report. Comparison uses only these fields:

- `version` (the scanner version under test; a version bump requires every expected file in `mesa-holdout` to be updated to that version)
- `label`
- `agents` (agent id, closure, full trifecta, PDP-on-all-contributing-paths, violation, contributing vertex ids, in the order the scanner emits them)
- `violation_count`

Any other field, including a path or source name, is ignored so the checkout directory cannot change the result. The two trees must contain the same relative JSON paths. A fixture without an expected file fails. An expected file without a fixture fails. Zero fixtures fails.

This document does not include fixture bodies. Do not add any.

## Token

Create a fine-grained personal access token with read-only Contents permission on `uddeshya-world/mesa-holdout` and no other repository. Store it as the environment secret `MESA_HOLDOUT_TOKEN` on the `holdout` environment of `uddeshya-world/mesa-ibi-scanner`, not as a repository secret.

The owner configures that environment with required reviewer `uddeshya-world` and deployment branches limited to `main`. A workflow dispatched from any other ref cannot receive the secret. Do not give the token to cloud-agent or implementer credentials. The human owner confirms holdout content is not readable by agent tokens before G0 is signed off.
