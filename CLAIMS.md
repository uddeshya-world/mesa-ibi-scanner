# Claims ledger

`claims/ledger.json` holds one row per published number. A row names the claim, the value, the command that prints it as JSON, the JSON path to the value, the commit, the tool versions and, for data-derived numbers, the dataset SHA-256.

- `python .github/harness/check_claims.py` checks the rows and the paper drafts under `docs/paper2/`. Every number in a draft must carry a `[[claim:CL-NNNN]]` marker. Section numbers, years and IDs such as G7, P-08 or SC-03 are exempt.
- `python .github/harness/check_claims.py --rerun` checks out each row's commit in a temporary worktree, runs its command and compares the value.

Rows start as `provisional`. A row becomes `reproduced` only after a `--rerun` pass. Adding or changing a row is a protected-path change that needs the owner's approval.

The ledger is empty. No MESA number has been measured under the G2, G6 or G8 pre-registrations yet.
