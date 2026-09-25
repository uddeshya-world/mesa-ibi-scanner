"""Build evidence/<task>.json from a real run. Do not hand-edit the output."""

from __future__ import annotations

import ast
import json
import os
import platform
import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path

from protected_paths import git, protected_changes, repo_root

ROOT = repo_root()


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    return subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )


def _parents(sha: str) -> list[str]:
    proc = subprocess.run(
        ["git", "rev-parse", f"{sha}^@"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return []
    return [item for item in proc.stdout.split() if item]


def _diff_names(parent: str, sha: str) -> list[str]:
    out = git("diff", "--no-renames", "--name-only", parent, sha)
    return [line for line in out.splitlines() if line]


def _rev_parse(ref: str) -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return None
    sha = proc.stdout.strip()
    return sha or None


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    return proc.returncode == 0


def _main_tip() -> str | None:
    for ref in ("origin/main", "main"):
        sha = _rev_parse(ref)
        if sha:
            return sha
    return None


def _on_first_parent(sha: str, tip: str) -> bool:
    proc = subprocess.run(
        ["git", "rev-list", "--first-parent", tip],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return False
    return sha in proc.stdout.split()


def _follow_merge(parents: list[str]) -> str:
    """Continue along the pull-request branch.

    GitHub's "Update branch" merge records the PR tip as the first parent and
    main as the second. Following the second parent would attest main.
    A merge of the PR into main records main as the first parent; follow the
    second parent in that case, including after that merge is itself main.
    Any other merge stays on the first parent.
    """
    first, second = parents[0], parents[1]
    main = _main_tip()
    if main is None:
        return first
    first_on_main = first == main or _is_ancestor(first, main)
    second_on_main = second == main or _is_ancestor(second, main)
    if second_on_main and not first_on_main:
        return first
    if first_on_main and not second_on_main:
        return second
    if first_on_main and second_on_main and _on_first_parent(first, main) and not _on_first_parent(second, main):
        return second
    return first


def _evidence_path(path: str) -> bool:
    return path.startswith("evidence/") and path.endswith(".json")


def attested_commit() -> str:
    """Commit whose tree, aside from evidence JSON, is the code under test.

    A file cannot embed the hash of the git commit that contains it.
    Evidence-only commits are skipped. Merge commits are followed only along
    the pull-request branch: an "Update branch" merge stays on the first
    parent, and a merge of the PR into main follows the second parent.
    Squash merges drop that parent link, so the repository must use merge
    commits only.
    """
    current = git("rev-parse", "HEAD").strip()
    for _ in range(50):
        parents = _parents(current)
        if len(parents) >= 2:
            current = _follow_merge(parents)
            continue
        if len(parents) == 1:
            names = _diff_names(parents[0], current)
            if names and all(_evidence_path(name) for name in names):
                current = parents[0]
                continue
        return current
    raise RuntimeError("attested commit walk did not settle")


def _ensure_worktree(task: str) -> None:
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    allowed = {f"evidence/{task}.json"}
    dirty: list[str] = []
    for line in proc.stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path not in allowed:
            dirty.append(path)
    if dirty:
        raise SystemExit("evidence: worktree dirty: " + ", ".join(dirty))


def _gate(task: str) -> str:
    path = ROOT / "tasks" / f"{task}.md"
    if not path.is_file():
        raise SystemExit(f"evidence: missing tasks/{task}.md")
    match = re.search(r"(?m)^Gate:\s*(\S+)\s*$", path.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f"evidence: tasks/{task}.md has no Gate line")
    return match.group(1)


def _pytest_summary(output: str, code: int) -> tuple[str, int, int]:
    passed = int(match.group(1)) if (match := re.search(r"(\d+) passed", output)) else 0
    failed = int(match.group(1)) if (match := re.search(r"(\d+) failed", output)) else 0
    errors = int(match.group(1)) if (match := re.search(r"(\d+) error", output)) else 0
    total = passed + failed + errors
    ok = code == 0 and failed == 0 and errors == 0 and total > 0
    return ("pass" if ok else "fail", passed, total)


def _property_seeds() -> list[int]:
    path = ROOT / "tests" / "test_properties.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    seeds: list[int] = []

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            is_random = (isinstance(func, ast.Attribute) and func.attr == "Random") or (
                isinstance(func, ast.Name) and func.id == "Random"
            )
            if (
                is_random
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, int)
            ):
                seeds.append(node.args[0].value)
            self.generic_visit(node)

    Visitor().visit(tree)
    return seeds


def _tool_version(dist: str) -> str:
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return "none"


def _check(check_id: str, result: str, cases: int | None = None, seed: object = None) -> dict[str, object]:
    item: dict[str, object] = {"id": check_id, "result": result}
    if cases is not None:
        item["cases"] = cases
    if seed is not None:
        item["seed"] = seed
    return item


def build(task: str) -> dict[str, object]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", task):
        raise SystemExit("evidence: TASK id contains unsupported characters")
    _ensure_worktree(task)
    gate = _gate(task)
    t0 = _run([sys.executable, ".github/harness/t0.py"])
    t1 = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--color=no",
            "tests/test_topology.py",
            "tests/test_topology_pdp_optional.py",
            "tests/test_cli_output.py",
        ]
    )
    t2 = _run([sys.executable, "-m", "pytest", "-q", "--color=no", "tests/test_properties.py"])
    t3 = _run([sys.executable, "-m", "pytest", "-q", "--color=no", "tests/test_closure.py"])
    t1_result, _t1_passed, t1_total = _pytest_summary(t1.stdout + t1.stderr, t1.returncode)
    t2_result, _t2_passed, t2_total = _pytest_summary(t2.stdout + t2.stderr, t2.returncode)
    t3_result, t3_passed, t3_total = _pytest_summary(t3.stdout + t3.stderr, t3.returncode)
    checks = [
        _check("T0", "pass" if t0.returncode == 0 else "fail"),
        _check("T1", t1_result, cases=t1_total),
        _check("T2", t2_result, cases=t2_total, seed=_property_seeds()),
        _check("T3", t3_result, cases=t3_total),
    ]
    for proc, label in ((t0, "T0"), (t1, "T1"), (t2, "T2"), (t3, "T3")):
        if proc.returncode != 0:
            sys.stderr.write(f"evidence: {label} failed\n")
            sys.stderr.write(proc.stdout)
            sys.stderr.write(proc.stderr)
    public = f"{t3_passed}/{t3_total}" if t3_total else "0/0"
    payload: dict[str, object] = {
        "task": task,
        "commit": attested_commit(),
        "gate": gate,
        "checks": checks,
        "golden": {
            "public": public,
            "holdout": {"result": "see-status", "status_context": "holdout"},
        },
        "benchmarks": [],
        "mutation_score": None,
        "protected_paths_changed": protected_changes(),
        "tool_versions": {
            "python": platform.python_version(),
            "pytest": _tool_version("pytest"),
            "ruff": _tool_version("ruff"),
            "mypy": _tool_version("mypy"),
            "hypothesis": _tool_version("hypothesis"),
            "jev": "none",
        },
        "reproduce": f"make evidence TASK={task}",
    }
    return payload


def write(task: str, payload: dict[str, object]) -> Path:
    target = ROOT / "evidence" / f"{task}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2) + "\n"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(target)
    return target


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: evidence.py TASK-0001", file=sys.stderr)
        return 2
    task = argv[1]
    payload = build(task)
    path = write(task, payload)
    print(f"wrote {path.relative_to(ROOT).as_posix()}")
    checks = payload["checks"]
    if not isinstance(checks, list):
        return 1
    if any(isinstance(item, dict) and item.get("result") != "pass" for item in checks):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
