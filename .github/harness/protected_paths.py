"""Protected-path matching shared by CI and evidence generation.

Patterns come from `.github/CODEOWNERS`. A path is protected when any
pattern lists an owner. Matching follows GitHub's CODEOWNERS rules closely
enough for the patterns this repo uses.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

REQUIRED_PATTERNS: tuple[str, ...] = (
    "/mesa_ibi_scanner/fixtures.py",
    "/tests/",
    "/schemas/",
    "/gates/",
    "/thresholds/",
    "/zones/",
    "/claims/",
    "/claims-ledger/",
    "/CLAIMS.md",
    "/tasks/",
    "/DECISIONS.md",
    "/.github/",
    "/Makefile",
)

OWNER = "@uddeshya-world"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root(),
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return proc.stdout


def parse_codeowners(text: str) -> list[tuple[str, tuple[str, ...]]]:
    rows: list[tuple[str, tuple[str, ...]]] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        pattern, owners = parts[0], tuple(parts[1:])
        if owners:
            rows.append((pattern, owners))
    return rows


def load_codeowners() -> list[tuple[str, tuple[str, ...]]]:
    path = repo_root() / ".github" / "CODEOWNERS"
    return parse_codeowners(path.read_text(encoding="utf-8"))


def _translate(pattern: str) -> str:
    """Translate a CODEOWNERS glob (no leading slash) to a full-match regex."""
    index = 0
    out: list[str] = []
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif pattern[index] == "*":
            out.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(pattern[index]))
            index += 1
    return "".join(out)


def _normalize(path: str) -> str:
    text = path.replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text.lstrip("/")


def path_matches(pattern: str, path: str) -> bool:
    normalized = _normalize(path)
    body = pattern.removeprefix("/")
    anchored = pattern.startswith("/")
    if body.endswith("/"):
        body = body + "**"
    regex = _translate(body)
    if anchored or "/" in pattern.strip("/"):
        return re.fullmatch(regex, normalized) is not None
    basename = normalized.rsplit("/", 1)[-1]
    return re.fullmatch(regex, basename) is not None


def matching_owners(path: str, rows: list[tuple[str, tuple[str, ...]]] | None = None) -> tuple[str, ...]:
    """Last matching CODEOWNERS pattern wins, as on GitHub."""
    chosen: tuple[str, ...] = ()
    for pattern, owners in rows if rows is not None else load_codeowners():
        if path_matches(pattern, path):
            chosen = owners
    return chosen


def is_protected(path: str, rows: list[tuple[str, tuple[str, ...]]] | None = None) -> bool:
    return bool(matching_owners(path, rows))


def assert_codeowners_contract() -> None:
    rows = load_codeowners()
    patterns = {pattern for pattern, _owners in rows}
    missing = [pattern for pattern in REQUIRED_PATTERNS if pattern not in patterns]
    if missing:
        raise RuntimeError("CODEOWNERS missing patterns: " + ", ".join(missing))
    for pattern, owners in rows:
        if OWNER not in owners:
            raise RuntimeError(f"CODEOWNERS pattern {pattern} is missing {OWNER}")
    samples = (
        ("/tests/", "tests/test_closure.py"),
        ("/Makefile", "Makefile"),
        ("/.github/", ".github/workflows/ci.yml"),
        ("/.github/", ".github/CODEOWNERS"),
        ("/mesa_ibi_scanner/fixtures.py", "mesa_ibi_scanner/fixtures.py"),
        ("/schemas/", "schemas/v0.1/mesa-topology.schema.json"),
        ("/schemas/", "schemas/examples/topology-hf-like.json"),
        ("/gates/", "gates/g0.yaml"),
        ("/thresholds/", "thresholds/example.yaml"),
        ("/zones/", "zones/production.yaml"),
        ("/DECISIONS.md", "DECISIONS.md"),
        ("/tasks/", "tasks/TASK-0001.md"),
        ("/claims/", "claims/ledger.json"),
        ("/CLAIMS.md", "CLAIMS.md"),
    )
    for pattern, sample in samples:
        if not path_matches(pattern, sample):
            raise RuntimeError(f"pattern {pattern} did not match {sample}")
    if path_matches("/Makefile", "docs/Makefile"):
        raise RuntimeError("Makefile pattern matched a nested path")
    if path_matches("/tests/", "mesa_ibi_scanner/graph.py"):
        raise RuntimeError("tests pattern matched scanner source")
    if is_protected("README.md"):
        raise RuntimeError("README.md must not be a protected path")
    if not is_protected(".github/harness/t0.py"):
        raise RuntimeError("harness scripts must be protected")


def base_ref() -> str:
    requested = os.environ.get("BASE_REF", "").strip()
    candidates = [requested] if requested else []
    candidates.extend(["origin/main", "main"])
    for candidate in candidates:
        if not candidate:
            continue
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", candidate],
            cwd=repo_root(),
            check=False,
            text=True,
            capture_output=True,
        )
        if proc.returncode == 0:
            return candidate
    raise RuntimeError("no base ref (tried BASE_REF, origin/main, main)")


def changed_files() -> list[str]:
    base = base_ref()
    out = git("diff", "--name-only", f"{base}...HEAD")
    return sorted({line for line in out.splitlines() if line})


def protected_changes() -> list[str]:
    rows = load_codeowners()
    return [path for path in changed_files() if is_protected(path, rows)]


def _self_check() -> None:
    assert_codeowners_contract()


if __name__ == "__main__":
    _self_check()
    print("protected_paths: ok")
