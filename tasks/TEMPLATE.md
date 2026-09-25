# Task spec template

Copy this file to `tasks/<id>.md`. The owner approves it before implementation starts. The body below is the Section 11 template.

# TASK-0412: Frontier export in scanner v0.4
Gate: G7
Design rules touched: 1 (deterministic authority), 2 (upward-only)
Goal: Export per-agent closure frontier as versioned, signed JSON.
Out of scope: PEP consumption (G-P2a).
Acceptance checks (must be merged before implementation):
  - P-07 frontier correctness on generated graphs (10,000 cases, seed 7)
  - Golden: fixtures/frontier/*.json incl. holdout family H-FR
  - B-01 does not regress more than 10%
Protected paths: fixtures/**, gates/**, schemas/**, thresholds/**
Evidence required: evidence/TASK-0412.json
