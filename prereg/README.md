# Pre-registration manifest

`manifest.json` holds the SHA-256 of each pre-registration file (gates g2, g6, g8, g9, the zone thresholds, `docs/BASERATE.md` and `docs/G2_SPIKE.md`). Regenerate it with `python .github/harness/prereg_manifest.py`, and check it with `--check`.

Git commit dates do not prove pre-registration, because the committer sets them. Before the first G2 spike, derive run or corpus run, the owner deposits `manifest.json` on Zenodo or OSF and records the deposit here:

| Deposit | DOI or URL | Date |
| --- | --- | --- |
| Pre-registration v1 | Zenodo skipped by the owner; see OpenTimestamps below | |

## OpenTimestamps proofs

Git commit dates are set by the committer, so they prove nothing to a sceptic. `manifest.json.ots` and `baserate-run-v1.json.ots` are [OpenTimestamps](https://opentimestamps.org) proofs, submitted 30 Sep 2026 to the public calendars before `corpus/sample.py` was run. Once they are upgraded, they anchor both files in the Bitcoin blockchain.

- `manifest.json`: hashes of the pre-registration files (gates g2, g6, g8, g9, zones, BASERATE, G2_SPIKE).
- `baserate-run-v1.json`: the base-rate inputs fixed before sampling. That is the frame hash (143,452 hits in 324 size slices, none capped), seed, target, the hashes of the sampling and runner code, and the commits of mesa-lab, mesa-ibi-derive and mesa-ibi-scanner.

- `DECISIONS.md.ots`: the proof for the current `../DECISIONS.md`, stamped 3 Oct 2026 after the owner amended disclosure point 3 to option 3 (hashed rows), still before sampling. Verify with `ots verify -f DECISIONS.md prereg/DECISIONS.md.ots`.
- `DECISIONS.md.2026-09-30.ots`: the proof for `DECISIONS.md` as of commit b9cb325 (the 30 Sep disclosure decision), kept so the history of the decision is verifiable. Verify against `git show b9cb325:DECISIONS.md`.

**Status, 3 Oct 2026.** `manifest.json.ots` and `baserate-run-v1.json.ots` are anchored in Bitcoin blocks 969240 to 969251, and `DECISIONS.md.2026-09-30.ots` in blocks 969247 to 969296. The 3 Oct `DECISIONS.md.ots` is pending; the sample waits until it shows a Bitcoin block. Proofs are upgraded on GitHub's runners by the `ots` workflow in mesa-ops, because the agent sandbox cannot reach the calendars.

Verify with `ots verify prereg/baserate-run-v1.json.ots`, which needs a Bitcoin node or a block explorer. `ots upgrade` completes a pending proof. The sample is drawn only after the proof shows a Bitcoin block, so the block time precedes every result.

A run is valid only if the files it used match a deposited manifest.
