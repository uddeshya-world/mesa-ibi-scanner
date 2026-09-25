"""Trusted driver that runs inside the holdout container.

The image contains the candidate wheel and this file only. Fixtures are mounted
read-only at ``/fixtures``. Expected files are not mounted. Stdout and stderr
of the candidate CLI are written to ``/outputs`` or discarded. This process
prints nothing.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

FIXTURES = Path(os.environ.get("HOLDOUT_FIXTURES", "/fixtures"))
OUTPUTS = Path(os.environ.get("HOLDOUT_OUTPUTS", "/outputs"))


def _fixture_files(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        raise RuntimeError("fixtures missing")
    found: dict[str, Path] = {}
    for path in root.rglob("*.json"):
        resolved = path.resolve()
        if not resolved.is_relative_to(root.resolve()):
            raise RuntimeError("path escaped fixtures")
        relative = resolved.relative_to(root.resolve())
        if any(part.startswith(".") for part in relative.parts):
            continue
        found[relative.as_posix()] = resolved
    if not found:
        raise RuntimeError("no fixtures")
    return found


def main() -> int:
    fixtures = _fixture_files(FIXTURES)
    for relative, fixture_path in sorted(fixtures.items()):
        target = (OUTPUTS / relative).resolve()
        if not target.is_relative_to(OUTPUTS.resolve()):
            return 1
        target.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            ["mesa-ibi-scan", "--input", str(fixture_path), "--format", "json"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode not in (0, 1) or not proc.stdout:
            return 1
        target.write_bytes(proc.stdout)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001 — container logs are discarded; do not print paths
        raise SystemExit(1) from None
