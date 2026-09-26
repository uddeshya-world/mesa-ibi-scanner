"""Claims ledger check (G11, VALIDATION.md rule 7).

Every number in a paper draft must cite a ledger row as [[claim:CL-NNNN]].
Every ledger row names the command, commit and (for data-derived numbers)
the dataset SHA-256 that reproduce it.

    python .github/harness/check_claims.py            # static checks
    python .github/harness/check_claims.py --rerun    # re-run each command at its commit and compare
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "claims" / "ledger.json"
DRAFTS = ROOT / "docs" / "paper2"
REQUIRED = ("id", "claim", "value", "command", "json_path", "commit", "tool_versions", "status")
STATUSES = ("provisional", "reproduced")
MARK = re.compile(r"\[\[claim:(CL-\d{4})\]\]")
# A digit run that is not a section number, a year, a list index, a heading, or inside a claim marker.
BARE_NUMBER = re.compile(r"(?<![\w.\-:/\[])(\d+(?:\.\d+)?%?)(?![\w\]])")
ALLOWED_LINE = re.compile(r"^\s*(#|\||<!--|```)")


def load_ledger(path: Path = LEDGER) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("claims", [])
    if not isinstance(rows, list):
        raise SystemExit("claims: ledger 'claims' must be a list")
    return rows


def check_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors = []
    seen = set()
    for i, r in enumerate(rows):
        where = r.get("id", f"row {i}")
        for k in REQUIRED:
            if k not in r or r[k] in (None, ""):
                errors.append(f"{where}: missing {k}")
        if not re.fullmatch(r"CL-\d{4}", str(r.get("id", ""))):
            errors.append(f"{where}: id must look like CL-0001")
        if r.get("id") in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(r.get("id"))
        if r.get("status") not in STATUSES:
            errors.append(f"{where}: status must be one of {STATUSES}")
        if not re.fullmatch(r"[0-9a-f]{40}", str(r.get("commit", ""))):
            errors.append(f"{where}: commit must be a full SHA")
        if r.get("dataset") and not re.fullmatch(r"[0-9a-f]{64}", str(r.get("dataset_sha256", ""))):
            errors.append(f"{where}: dataset rows need dataset_sha256")
    return errors


def check_drafts(rows: list[dict[str, Any]], drafts: Path = DRAFTS) -> list[str]:
    ids = {r.get("id") for r in rows}
    errors = []
    for md in sorted(drafts.glob("*.md")):
        in_code = False
        for n, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            for cid in MARK.findall(line):
                if cid not in ids:
                    errors.append(f"{md.name}:{n}: {cid} not in ledger")
            if in_code or ALLOWED_LINE.match(line):
                continue
            stripped = re.sub(r"^\s*(?:\d+\.|[-*])\s+", "", MARK.sub("", line))
            stripped = re.sub(r"\b(?:Sections?|sections?|Figure|Table|G|P|SC|B|A|T|BR)[- ]?\d+", "", stripped)
            stripped = re.sub(r"\b(?:19|20)\d\d\b", "", stripped)
            for num in BARE_NUMBER.findall(stripped):
                errors.append(f"{md.name}:{n}: number '{num}' without a [[claim:...]] marker")
    return errors


def _extract(doc: Any, path: str) -> Any:
    cur = doc
    for part in path.split("."):
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


def rerun(rows: list[dict[str, Any]]) -> list[str]:
    errors = []
    for r in rows:
        with tempfile.TemporaryDirectory() as tmp:
            wt = Path(tmp) / "wt"
            add = subprocess.run(["git", "worktree", "add", "--detach", str(wt), r["commit"]], cwd=ROOT,
                                 capture_output=True, text=True, check=False)
            if add.returncode != 0:
                errors.append(f"{r['id']}: cannot check out {r['commit']}")
                continue
            try:
                proc = subprocess.run(r["command"], cwd=wt, shell=True, capture_output=True, text=True, check=False)
                value = _extract(json.loads(proc.stdout), r["json_path"])
                if value != r["value"]:
                    errors.append(f"{r['id']}: reproduced {value!r}, ledger says {r['value']!r}")
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                errors.append(f"{r['id']}: rerun failed ({exc})")
            finally:
                subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=ROOT, capture_output=True,
                               check=False)
    return errors


def main(argv: list[str]) -> int:
    rows = load_ledger()
    errors = check_rows(rows) + check_drafts(rows)
    if "--rerun" in argv:
        errors += rerun(rows)
    for e in errors:
        print(f"claims: {e}")
    print("claims: fail" if errors else f"claims: pass ({len(rows)} rows)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
