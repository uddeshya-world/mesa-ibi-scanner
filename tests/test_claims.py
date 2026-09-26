"""T1 unit: claims-ledger checker (G11)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("check_claims", ROOT / ".github" / "harness" / "check_claims.py")
assert _spec and _spec.loader
cc = importlib.util.module_from_spec(_spec)
sys.modules["check_claims"] = cc
_spec.loader.exec_module(cc)

ROW = {
    "id": "CL-0001",
    "claim": "B-01 evaluate time is under the 30 s target",
    "value": "pass",
    "command": "python benchmarks/b01_batch_closure.py",
    "json_path": "result",
    "commit": "0" * 40,
    "tool_versions": {"python": "3.12.3"},
    "status": "provisional",
}


def test_valid_row_passes():
    assert cc.check_rows([dict(ROW)]) == []


def test_missing_fields_and_bad_commit_fail():
    bad = dict(ROW)
    bad.pop("command")
    bad["commit"] = "abc"
    errs = cc.check_rows([bad])
    assert any("missing command" in e for e in errs) and any("full SHA" in e for e in errs)


def test_dataset_row_needs_hash():
    row = dict(ROW, dataset="corpus/manifest.json")
    assert any("dataset_sha256" in e for e in cc.check_rows([row]))


def test_duplicate_ids_fail():
    assert any("duplicate" in e for e in cc.check_rows([dict(ROW), dict(ROW)]))


def test_bare_number_in_draft_fails_and_marked_number_passes(tmp_path):
    (tmp_path / "d.md").write_text("Prevalence was 42% in the corpus.\n", encoding="utf-8")
    assert cc.check_drafts([dict(ROW)], tmp_path)
    (tmp_path / "d.md").write_text("Prevalence was [[claim:CL-0001]] in the corpus (Section 3, 2026).\n", encoding="utf-8")
    assert cc.check_drafts([dict(ROW)], tmp_path) == []


def test_unknown_claim_marker_fails(tmp_path):
    (tmp_path / "d.md").write_text("See [[claim:CL-0099]].\n", encoding="utf-8")
    assert any("CL-0099" in e for e in cc.check_drafts([dict(ROW)], tmp_path))


def test_repository_ledger_and_drafts_pass():
    rows = cc.load_ledger()
    assert cc.check_rows(rows) == [] and cc.check_drafts(rows) == []
