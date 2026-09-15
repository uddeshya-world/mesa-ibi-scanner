"""CLI exit-code and format tests (json / sarif / text)."""

from __future__ import annotations

import json
from pathlib import Path

from mesa_ibi_scanner.cli import main

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = str(ROOT / "schemas" / "examples" / "topology-hf-like.json")


def test_exit_code_nonzero_on_violation():
    rc = main(["--fixture", "hf_like", "--exit-code", "--format", "text"])
    assert rc == 1


def test_exit_code_zero_when_gated():
    rc = main(["--fixture", "hf_like_gated", "--exit-code", "--format", "text"])
    assert rc == 0


def test_exit_code_with_input_topology():
    rc = main(["--input", EXAMPLE, "--exit-code", "--format", "json"])
    assert rc == 1


def test_sarif_contains_results(capsys):
    rc = main(["--fixture", "hf_like", "--format", "sarif"])
    assert rc == 0  # without --exit-code
    out = capsys.readouterr().out
    doc = json.loads(out)
    assert doc["version"] == "2.1.0"
    assert "runs" in doc and len(doc["runs"]) == 1
    results = doc["runs"][0]["results"]
    assert len(results) >= 1
    assert results[0]["ruleId"] == "MESA-INV-01"
    assert results[0]["level"] == "error"
    assert "message" in results[0] and "text" in results[0]["message"]


def test_sarif_empty_results_when_no_violation(capsys):
    rc = main(["--fixture", "hf_like_gated", "--format", "sarif", "--exit-code"])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["runs"][0]["results"] == []


def test_json_format_has_violation_count(capsys):
    rc = main(["--input", EXAMPLE, "--format", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["violation_count"] >= 1
    assert payload["input"] == EXAMPLE
    assert any(a["violation"] for a in payload["agents"])


def test_schema_error_exit_2(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"vertices": [], "edges": []}', encoding="utf-8")
    rc = main(["--input", str(bad), "--format", "text"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "error:" in err
