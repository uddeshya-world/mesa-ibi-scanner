# Holdout fixtures

`mesa-holdout` is a private repository. The human owner creates it. Implementer agents do not get a checkout, a token, or fixture contents.

CI checks the repository out with the Actions secret `MESA_HOLDOUT_TOKEN` and runs those fixtures through the scanner already installed in this repo. The job prints one line and nothing else:

- `holdout: pass`
- `holdout: fail`
- `holdout: not configured` when `MESA_HOLDOUT_TOKEN` is unset or blank

`holdout: not configured` fails the job. An empty corpus, a failed clone, a schema or load error, or a result mismatch also fails the job. None of those cases print fixture names, file contents, paths, or diffs.

## Layout the owner commits

```text
fixtures/**/*.json
expected/<same relative path>.json
```

Every `*.json` file under `fixtures/` is a topology document. This repo validates it with the local schema `schemas/v0.1/mesa-topology.schema.json`. That check does not fetch the schema `$id`.

The matching file under `expected/` is a scanner JSON report. Comparison uses only these fields:

- `version` (the scanner version under test)
- `label`
- `agents` (agent id, closure, full trifecta, PDP-on-all-contributing-paths, violation, contributing vertex ids, in the order the scanner emits them)
- `violation_count`

Any other field, including a path or source name, is ignored so the checkout directory cannot change the result. The two trees must contain the same relative JSON paths. A fixture without an expected file fails. An expected file without a fixture fails. Zero fixtures fails.

This document does not include fixture bodies. Do not add any.

## Token

Create a fine-grained personal access token with read-only Contents permission on `uddeshya-world/mesa-holdout` and no other repository. Store it as the Actions secret `MESA_HOLDOUT_TOKEN` on `uddeshya-world/mesa-ibi-scanner`. Do not give that token to cloud-agent or implementer credentials. The human owner confirms holdout content is not readable by agent tokens before G0 is signed off.
