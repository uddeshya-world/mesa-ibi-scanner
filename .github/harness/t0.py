"""T0 static checks: lint, types, schema, licence, secrets, version consistency.

No network calls. Fixture documents are validated against the local v0.1
schemas. The redirect stub at schemas/mesa-acm.schema.json is not fetched.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from importlib import metadata
from pathlib import Path
from typing import Any, NoReturn

from protected_paths import assert_codeowners_contract, repo_root

ROOT = repo_root()

DEFECT_SELECT = "E9,F821,F822,F823,F841"

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private-key",
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----"),
    ),
    ("aws-access-key-id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-pat", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("github-fine-grained-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{82}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "aws-secret-access-key",
        re.compile(r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/+=]{40}['\"]"),
    ),
)

SKIP_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
}

TEXT_SUFFIXES = {
    ".cff",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def _fail(message: str) -> NoReturn:
    raise SystemExit(message)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def _pinned_tools() -> dict[str, str]:
    path = ROOT / ".github" / "harness" / "requirements-t0.txt"
    pins: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if "==" not in line:
            _fail(f"t0 pin is not exact: {line}")
        name, version = line.split("==", 1)
        pins[name.strip()] = version.strip()
    return pins


def check_tool_versions() -> None:
    for name, expected in _pinned_tools().items():
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            _fail(
                f"t0 missing {name}=={expected}; "
                "pip install -r .github/harness/requirements-t0.txt"
            )
        if installed != expected:
            _fail(f"t0 {name} {installed} != pinned {expected}")


def _fingerprint(diag: dict[str, Any]) -> tuple[str, str, int, str]:
    filename = Path(str(diag["filename"])).resolve()
    relative = filename.relative_to(ROOT).as_posix()
    location = diag["location"]
    if not isinstance(location, dict):
        _fail("ruff diagnostic missing location")
    column = location["column"]
    if not isinstance(column, int):
        _fail("ruff diagnostic missing column")
    return (relative, str(diag["code"]), column, str(diag["message"]))


def check_lint() -> None:
    defect = _run([sys.executable, "-m", "ruff", "check", "--select", DEFECT_SELECT, "."])
    if defect.returncode != 0:
        sys.stderr.write(defect.stdout)
        sys.stderr.write(defect.stderr)
        _fail("t0 lint: defect rules failed")
    full = _run([sys.executable, "-m", "ruff", "check", "--output-format=json", "."])
    try:
        data = json.loads(full.stdout or "[]")
    except json.JSONDecodeError:
        sys.stderr.write(full.stdout)
        sys.stderr.write(full.stderr)
        _fail("t0 lint: ruff did not return JSON")
    if not isinstance(data, list):
        _fail("t0 lint: ruff JSON was not a list")
    current: Counter[tuple[str, str, int, str]] = Counter()
    for item in data:
        if isinstance(item, dict):
            current[_fingerprint(item)] += 1
    baseline_path = ROOT / ".github" / "harness" / "ruff-baseline.json"
    baseline_items = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline: Counter[tuple[str, str, int, str]] = Counter()
    for item in baseline_items:
        baseline[(item["path"], item["code"], int(item["column"]), item["message"])] += 1
    new = [(key, count, baseline[key]) for key, count in current.items() if count > baseline[key]]
    if new:
        for key, count, allowed in new:
            path, code, column, message = key
            print(f"t0 lint new: {path}:{column} {code} x{count} (baseline {allowed}) {message}")
        _fail("t0 lint: new findings beyond the v0.3.2 baseline")


def check_types() -> None:
    proc = _run(
        [
            sys.executable,
            "-m",
            "mypy",
            "mesa_ibi_scanner",
            "tests",
            ".github/harness",
        ]
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        _fail("t0 types: mypy failed")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_topology(doc: Any, label: str) -> None:
    from mesa_ibi_scanner.topology import TopologyError, validate_topology_document

    try:
        validate_topology_document(doc)
    except TopologyError as exc:
        _fail(f"t0 schema: {label}: {exc}")


def _validate_acm(doc: Any, label: str) -> None:
    from jsonschema import Draft202012Validator

    schema_path = ROOT / "schemas" / "v0.1" / "mesa-acm.schema.json"
    schema = _load_json(schema_path)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(doc),
        key=lambda err: list(err.absolute_path),
    )
    if errors:
        first = errors[0]
        loc = ".".join(str(part) for part in first.absolute_path) or "(root)"
        _fail(f"t0 schema: {label}: {loc}: {first.message}")


def _graph_document(graph: Any) -> dict[str, Any]:
    from mesa_ibi_scanner.graph import EstateGraph, VertexKind

    if not isinstance(graph, EstateGraph):
        _fail("t0 schema: fixture did not return an EstateGraph")
    vertices: list[dict[str, Any]] = []
    for vid in sorted(graph.vertices):
        vertex = graph.vertices[vid]
        kind = vertex.kind.value if isinstance(vertex.kind, VertexKind) else str(vertex.kind)
        item: dict[str, Any] = {
            "id": vertex.id,
            "kind": kind,
            "w": [int(vertex.w[0]), int(vertex.w[1]), int(vertex.w[2])],
        }
        if vertex.tags:
            item["tags"] = sorted(vertex.tags)
        vertices.append(item)
    edges: list[dict[str, Any]] = []
    for edge in graph.edges:
        item = {
            "src": edge.src,
            "dst": edge.dst,
            "flow_type": edge.flow_type,
            "pdp_gate": bool(edge.pdp_gate),
        }
        if edge.label:
            item["label"] = edge.label
        edges.append(item)
    document: dict[str, Any] = {
        "topology_version": "0.1.0",
        "vertices": vertices,
        "edges": edges,
    }
    return document


def check_schemas() -> None:
    from mesa_ibi_scanner.fixtures import FIXTURES

    examples = sorted((ROOT / "schemas" / "examples").glob("*.json"))
    if not examples:
        _fail("t0 schema: no example documents")
    for path in examples:
        doc = _load_json(path)
        if not isinstance(doc, dict):
            _fail(f"t0 schema: {path.relative_to(ROOT)} is not an object")
        relative = path.relative_to(ROOT).as_posix()
        if "acm_version" in doc:
            _validate_acm(doc, relative)
        elif "vertices" in doc:
            _validate_topology(doc, relative)
        else:
            _fail(f"t0 schema: {relative} is neither ACM nor topology")
    if not FIXTURES:
        _fail("t0 schema: no built-in fixtures")
    for name, factory in sorted(FIXTURES.items()):
        _validate_topology(_graph_document(factory()), f"built-in fixture {name}")


def _spdx_is_apache(text: str) -> bool:
    for line in text.splitlines()[:40]:
        if "SPDX-License-Identifier:" not in line:
            continue
        token = line.split("SPDX-License-Identifier:", 1)[1].strip()
        if token not in {"Apache-2.0", "Apache-2.0+"}:
            return False
    return True


def check_licence() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    if "Apache License" not in license_text or "Version 2.0" not in license_text:
        _fail("t0 licence: LICENSE is not Apache-2.0")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if "Apache-2.0" not in pyproject:
        _fail("t0 licence: pyproject.toml does not declare Apache-2.0")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    if not re.search(r"(?m)^license:\s*Apache-2\.0\s*$", citation):
        _fail("t0 licence: CITATION.cff license is not Apache-2.0")
    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    if zenodo.get("license") != "apache-2.0":
        _fail("t0 licence: .zenodo.json license is not apache-2.0")
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:40])
        if not _spdx_is_apache(head):
            _fail(f"t0 licence: non-Apache SPDX in {path.relative_to(ROOT)}")
        if "GNU General Public License" in head or "MIT License" in head:
            _fail(f"t0 licence: foreign header in {path.relative_to(ROOT)}")


def _iter_text_files() -> list[Path]:
    found: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            "Makefile",
            "CODEOWNERS",
            "LICENSE",
            "NOTICE",
        }:
            continue
        if path.stat().st_size > 1_000_000:
            continue
        found.append(path)
    return sorted(found)


def check_secrets() -> None:
    hits: list[str] = []
    for path in _iter_text_files():
        data = path.read_bytes()
        if b"\0" in data:
            continue
        text = data.decode("utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for name, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    hits.append(f"{path.relative_to(ROOT)}:{lineno} {name}")
    if hits:
        for hit in hits:
            print(f"t0 secrets: {hit}")
        _fail("t0 secrets: findings")


def check_version_consistency() -> None:
    pyproject = re.search(
        r'version\s*=\s*"([^"]+)"',
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
    )
    init = re.search(
        r'__version__\s*=\s*"([^"]+)"',
        (ROOT / "mesa_ibi_scanner" / "__init__.py").read_text(encoding="utf-8"),
    )
    citation = re.search(
        r"^version:\s*(\S+)",
        (ROOT / "CITATION.cff").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))["version"]
    if not pyproject or not init or not citation:
        _fail("t0 version: could not read one of the version fields")
    versions = {pyproject.group(1), init.group(1), citation.group(1), zenodo}
    print(
        f"pyproject={pyproject.group(1)} init={init.group(1)} "
        f"cff={citation.group(1)} zenodo={zenodo}"
    )
    if len(versions) != 1:
        _fail("version drift across pyproject.toml / __init__ / CITATION.cff / .zenodo.json")


def main() -> int:
    assert_codeowners_contract()
    checks = (
        ("tools", check_tool_versions),
        ("lint", check_lint),
        ("types", check_types),
        ("schema", check_schemas),
        ("licence", check_licence),
        ("secrets", check_secrets),
        ("version", check_version_consistency),
    )
    failed = False
    for name, fn in checks:
        try:
            fn()
        except SystemExit as exc:
            print(f"t0 {name}: fail")
            if exc.code not in (None, 0, 1):
                print(exc.code)
            failed = True
            continue
        print(f"t0 {name}: pass")
    if failed:
        return 1
    print("t0: pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
