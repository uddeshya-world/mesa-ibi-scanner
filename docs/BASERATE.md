# Base-rate study: corpus criteria and analysis plan

Status: **pre-registration draft** for TASK-0010 (G8, G9). Owner approval pending. No corpus run may start before the owner merges this file and `gates/g8.yaml`. A run made before approval, or after a later change to these criteria, is invalid (VALIDATION.md rule 5).

## 1. Question

How common are blackboard-capable services in real multi-principal cloud estates? A **blackboard-capable** service has at least two writer principals and at least one reader principal (docs/DERIVATION.md section 4).

The answer decides the framing: prevalence if the rate is high, conditional risk if it is low (roadmap Section 14). Either result is published.

## 2. Unit of analysis

One **environment** is one Terraform root module (a directory with a `terraform` or `provider` block, or the module's `examples/` root) at a pinned commit.

## 3. Sampling frame

- **Source:** public GitHub repositories with HCL files that declare at least two `aws_iam_role` resources and at least one of `aws_lambda_function`, `aws_ecs_task_definition` or `aws_instance`.
- **Query:** GitHub code search `resource "aws_iam_role" language:HCL`. It is run once, on a date recorded in the manifest. The full result list (repository, path, commit SHA) is saved to `corpus/frame.json` before sampling.
- **Sampling:** a uniform random sample without replacement from the frame, seed `20261001`, drawn in frame order. Environments are drawn until 100 have passed the inclusion criteria, or the frame is exhausted.
- **Target size:** 100 included environments. The roadmap range is 80 to 120. Fewer than 80 is reported as a limitation, and the study still runs.

## 4. Inclusion and exclusion

An environment is **included** when all of these hold:

1. `mesa-ibi-derive` parses it without error, from HCL (no plan and no credentials; see section 6).
2. At least two distinct IAM roles are attached to compute.
3. At least one data service (docs/DERIVATION.md section 6 list) is declared.

Exclusions, each recorded with its reason:

- A fork of a repository already in the sample (only the earliest-created repository counts).
- Archived tutorials whose README says the code is incomplete.
- Environments whose IAM is entirely in `var.` inputs with no defaults (no grants can be resolved).
- Repositories whose licence forbids redistribution of derived data. The environment is still counted, but its row is published without paths.

Exclusions are reported with counts per reason.

## 5. Measures

| ID | Measure | Definition |
| --- | --- | --- |
| BR-1 | Blackboard prevalence | Fraction of included environments with at least one blackboard-capable service |
| BR-2 | Channel prevalence | Fraction with at least one `channel` service (one writer, a different reader) |
| BR-3 | Services per environment | Median and IQR of blackboard-capable services per environment |
| BR-4 | Review load | Median share of facts marked `requires-review` |
| BR-5 | Wildcard share | Fraction of environments with any `Resource: "*"` grant to a data-service type |

**Primary outcome:** BR-1.

## 6. Derivation settings (frozen)

- Input: HCL converted to plan-shaped JSON by `mesa-lab/baserate` (configuration references only; no provider calls).
- Every role attached to compute is treated as an agent principal. The corpus does not say which roles run agents, so BR-1 measures **capability**, not agent use. This limitation is stated in every report.
- Zone `production`, memory `unbounded` for every agent. Neither affects BR-1.
- Derive version and commit are recorded in the manifest. Changing either invalidates the run.

## 7. Analysis plan (G9)

- **Interval:** 95% Wilson score interval for BR-1 and BR-2.
- **Negative cases:** every included environment with no blackboard-capable service is listed with its service and principal counts. The findings note discusses them.
- **Derivation accuracy on a sample:** 10 included environments drawn with seed `20261002`. The owner hand-verifies each topology and reports edge precision and recall and shared-service recall with the G2 T4 definitions.
- **Framing rule (pre-registered):**
  - Lower 95% bound of BR-1 at least 0.2: report as "common".
  - Upper bound below 0.2: report as "uncommon"; switch to conditional-risk framing.
  - Otherwise: "inconclusive".

## 8. Reproducibility

`make reproduce-baserate` in `mesa-lab` rebuilds every number from `corpus/manifest.json` (repository, path, commit, inclusion decision) and prints the dataset SHA-256. The raw dataset and manifest get a versioned DOI after the owner approves the run.
