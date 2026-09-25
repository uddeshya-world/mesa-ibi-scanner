"""Run private mesa-holdout fixtures. Logs are pass, fail, or not configured.

Fixture names, file contents, paths, and diffs are never printed.
"""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path


def _comparable(payload: dict[str, object]) -> dict[str, object]:
    return {
        "version": payload.get("version"),
        "label": payload.get("label"),
        "agents": payload.get("agents"),
        "violation_count": payload.get("violation_count"),
    }


def _json_files(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    found: dict[str, Path] = {}
    for path in root.rglob("*.json"):
        resolved = path.resolve()
        if not resolved.is_relative_to(root.resolve()):
            raise RuntimeError("path escaped holdout root")
        if any(part.startswith(".") for part in resolved.relative_to(root.resolve()).parts):
            continue
        found[resolved.relative_to(root.resolve()).as_posix()] = resolved
    return found


def _evaluate(checkout: Path) -> bool:
    import json

    from mesa_ibi_scanner.graph import evaluate_invariant
    from mesa_ibi_scanner.report import results_payload
    from mesa_ibi_scanner.topology import load_topology

    fixture_root = checkout / "fixtures"
    expected_root = checkout / "expected"
    fixtures = _json_files(fixture_root)
    expected = _json_files(expected_root)
    if not fixtures or set(fixtures) != set(expected):
        return False
    for relative, fixture_path in sorted(fixtures.items()):
        graph = load_topology(fixture_path)
        payload = results_payload(
            evaluate_invariant(graph),
            source="holdout",
            source_kind="input",
        )
        expected_payload = json.loads(expected[relative].read_text(encoding="utf-8"))
        if not isinstance(expected_payload, dict):
            return False
        if _comparable(payload) != _comparable(expected_payload):
            return False
    return True


def _clone(token: str, dest: Path) -> None:
    askpass = dest.parent / "askpass.sh"
    askpass.write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        '  *sername*) printf "%s\\n" "x-access-token" ;;\n'
        '  *) printf "%s\\n" "$MESA_HOLDOUT_TOKEN" ;;\n'
        "esac\n",
        encoding="utf-8",
    )
    askpass.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    env = os.environ.copy()
    env["MESA_HOLDOUT_TOKEN"] = token
    env["GIT_ASKPASS"] = str(askpass)
    env["SSH_ASKPASS"] = str(askpass)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    proc = subprocess.run(
        [
            "git",
            "-c",
            "credential.helper=",
            "clone",
            "--depth",
            "1",
            "https://github.com/uddeshya-world/mesa-holdout.git",
            str(dest),
        ],
        check=False,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0 or not dest.is_dir():
        raise RuntimeError("clone failed")


def _run(token: str) -> bool:
    work = Path(tempfile.mkdtemp(prefix="mesa-holdout-"))
    checkout = work / "repo"
    try:
        _clone(token, checkout)
        return _evaluate(checkout)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    token = os.environ.get("MESA_HOLDOUT_TOKEN", "").strip()
    if not token:
        print("holdout: not configured")
        return 1
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            passed = _run(token)
    except Exception:  # noqa: BLE001 — logs must not contain fixture paths or tracebacks
        print("holdout: fail")
        return 1
    print("holdout: pass" if passed else "holdout: fail")
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001 — logs must not contain fixture paths or tracebacks
        print("holdout: fail")
        raise SystemExit(1) from None
