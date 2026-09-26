"""T1 unit: ACM v1 runtime-extension drafts validate real producer output (decision records from mesa-pep)."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def _schema(name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((ROOT / "schemas" / "v0.3-draft" / name).read_text(encoding="utf-8")))


def _lines(name: str) -> list[dict]:
    return [json.loads(x) for x in (ROOT / "fixtures" / "runtime" / name).read_text(encoding="utf-8").splitlines() if x.strip()]


def test_mesa_pep_records_validate():
    v = _schema("mesa-decision-record.schema.json")
    recs = _lines("decision-records.jsonl")
    assert recs
    for r in recs:
        assert not list(v.iter_errors(r)), r["record_id"]


def test_final_verdict_never_weaker_than_deterministic_in_fixtures():
    order = {"ALLOW": 0, "HOLD": 1, "BLOCK": 2}
    for r in _lines("decision-records.jsonl"):
        assert order[r["final_verdict"]] >= order[r["deterministic_verdict"]]


def test_record_missing_a_mandatory_field_is_rejected():
    v = _schema("mesa-decision-record.schema.json")
    r = _lines("decision-records.jsonl")[0]
    r.pop("frontier_version")
    assert list(v.iter_errors(r))


def test_observed_edge_events_validate():
    v = _schema("mesa-observed-edge.schema.json")
    for e in _lines("observed-edges.jsonl"):
        assert not list(v.iter_errors(e))
