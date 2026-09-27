# SPDX-License-Identifier: Apache-2.0
"""T6: fail when a benchmark timing regresses more than 10% against the previous nightly.

    python .github/harness/bench_regress.py CURRENT.json [PREVIOUS.json] KEY [KEY ...]

With no previous result (first run, or the artifact expired) it records the
current numbers and passes. Absolute targets are checked by the benchmark
itself.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LIMIT = 0.10


def main(argv: list[str]) -> int:
    current = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    prev_path = Path(argv[1])
    keys = argv[2:]
    if not prev_path.is_file():
        print("t6: no previous nightly result; baseline recorded")
        return 0
    previous = json.loads(prev_path.read_text(encoding="utf-8"))
    failed = False
    for key in keys:
        before, after = previous.get(key), current.get(key)
        if not isinstance(before, (int, float)) or not isinstance(after, (int, float)) or before <= 0:
            print(f"t6 {key}: not comparable")
            continue
        change = after / before - 1.0
        verdict = "fail" if change > LIMIT else "pass"
        failed |= verdict == "fail"
        print(f"t6 {key}: {before} -> {after} ({change:+.1%}) {verdict}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
