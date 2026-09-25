"""Rebuild evidence JSON changed by this branch and fail on any byte mismatch.

Skips when the branch does not add or modify an evidence file.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from protected_paths import changed_files, repo_root

ROOT = repo_root()


def main() -> int:
    evidence_files = [
        path
        for path in changed_files()
        if path.startswith("evidence/") and path.endswith(".json")
    ]
    if not evidence_files:
        print("evidence: no evidence file in PR; skipping")
        return 0
    failed = False
    for relative in evidence_files:
        task = Path(relative).stem
        before = (ROOT / relative).read_bytes()
        proc = subprocess.run(
            ["make", "evidence", f"TASK={task}"],
            cwd=ROOT,
            check=False,
        )
        after = (ROOT / relative).read_bytes()
        if proc.returncode != 0 or before != after:
            subprocess.run(["git", "diff", "--", relative], cwd=ROOT, check=False)
            print(f"evidence: mismatch {relative}")
            failed = True
    if failed:
        return 1
    print("evidence: match")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"evidence: fail ({exc})")
        sys.exit(1)
