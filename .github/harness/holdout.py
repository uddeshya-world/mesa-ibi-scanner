"""Run private mesa-holdout fixtures. Logs are pass, fail, or not configured.

Fixture names, file contents, paths, and diffs are never printed.

Comparison includes the scanner ``version`` field. A version bump needs the
expected files in mesa-holdout updated. See docs/HOLDOUT.md.

Subcommands used by the owner-dispatched workflow (trusted code only):

- ``clone DEST`` clones mesa-holdout. This is the only command that reads
  ``MESA_HOLDOUT_TOKEN``.
- ``compare ROOT OUTPUTS`` compares ``ROOT/expected`` with JSON files the
  candidate wrote. It does not import or run the candidate.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


def _comparable(payload: dict[str, object]) -> dict[str, object]:
    # ``version`` is included on purpose. See docs/HOLDOUT.md.
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


def compare_outputs(holdout_root: Path, output_root: Path) -> bool:
    """Compare candidate JSON files with expected files. Never runs candidate code."""
    fixtures = _json_files(holdout_root / "fixtures")
    expected = _json_files(holdout_root / "expected")
    produced = _json_files(output_root)
    if not fixtures or set(fixtures) != set(expected) or set(produced) != set(expected):
        return False
    for relative, expected_path in sorted(expected.items()):
        produced_payload = json.loads(produced[relative].read_text(encoding="utf-8"))
        expected_payload = json.loads(expected_path.read_text(encoding="utf-8"))
        if not isinstance(produced_payload, dict) or not isinstance(expected_payload, dict):
            return False
        if _comparable(produced_payload) != _comparable(expected_payload):
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
    askpass.unlink(missing_ok=True)
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


def _token() -> str:
    return os.environ.get("MESA_HOLDOUT_TOKEN", "").strip()


def _report(passed: bool) -> int:
    print("holdout: pass" if passed else "holdout: fail")
    return 0 if passed else 1


def _local() -> int:
    token = _token()
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
    return _report(passed)


def _clone_command(dest: Path) -> int:
    token = _token()
    if not token:
        print("holdout: not configured")
        return 1
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            _clone(token, dest)
    except Exception:  # noqa: BLE001 — logs must not contain fixture paths or tracebacks
        print("holdout: fail")
        return 1
    return 0


def _compare_command(holdout_root: Path, output_root: Path) -> int:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            passed = compare_outputs(holdout_root, output_root)
    except Exception:  # noqa: BLE001 — logs must not contain fixture paths or tracebacks
        print("holdout: fail")
        return 1
    return _report(passed)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return _local()
    if args[0] == "clone" and len(args) == 2:
        return _clone_command(Path(args[1]))
    if args[0] == "compare" and len(args) == 3:
        return _compare_command(Path(args[1]), Path(args[2]))
    print("holdout: fail")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001 — logs must not contain fixture paths or tracebacks
        print("holdout: fail")
        raise SystemExit(1) from None
