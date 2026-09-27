# SPDX-License-Identifier: Apache-2.0
"""Write or check prereg/manifest.json: SHA-256 of every pre-registration file.

Git commit dates can be set by whoever commits, so they do not prove to a
reviewer that criteria were fixed before a run. The owner deposits this
manifest on Zenodo or OSF, which gives an external timestamp.

    python .github/harness/prereg_manifest.py          # write
    python .github/harness/prereg_manifest.py --check  # fail if a file changed
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "prereg" / "manifest.json"
FILES = [
    "gates/g2.yaml",
    "gates/g6.yaml",
    "gates/g8.yaml",
    "gates/g9.yaml",
    "thresholds/zones.json",
    "docs/BASERATE.md",
    "docs/G2_SPIKE.md",
]


def digests() -> dict[str, str]:
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES}


def main() -> int:
    current = digests()
    if "--check" in sys.argv:
        recorded = json.loads(MANIFEST.read_text(encoding="utf-8"))["sha256"]
        changed = sorted(f for f in FILES if recorded.get(f) != current[f])
        if changed:
            print("prereg: changed since manifest: " + ", ".join(changed))
            return 1
        print("prereg: manifest matches")
        return 0
    MANIFEST.parent.mkdir(exist_ok=True)
    doc = {"algorithm": "sha256", "sha256": current}
    MANIFEST.write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(f"wrote {MANIFEST.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
