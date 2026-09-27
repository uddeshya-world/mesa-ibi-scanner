# Pre-registration manifest

`manifest.json` holds the SHA-256 of each pre-registration file (gates g2, g6, g8, g9, the zone thresholds, `docs/BASERATE.md` and `docs/G2_SPIKE.md`). Regenerate it with `python .github/harness/prereg_manifest.py`, and check it with `--check`.

Git commit dates do not prove pre-registration, because the committer sets them. Before the first G2 spike, derive run or corpus run, the owner deposits `manifest.json` on Zenodo or OSF and records the deposit here:

| Deposit | DOI or URL | Date |
| --- | --- | --- |
| Pre-registration v1 | | |

A run is valid only if the files it used match a deposited manifest.
