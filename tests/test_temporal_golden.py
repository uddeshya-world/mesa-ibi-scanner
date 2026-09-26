"""T3 golden: temporal fixtures (SC-03, SC-10) under fixtures/temporal/."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mesa_ibi_scanner.lattice import document_to_lgraph, evaluate
from mesa_ibi_scanner.temporal import evaluate_timeline
from mesa_ibi_scanner.topology import validate_timeline_document

ROOT = Path(__file__).resolve().parents[1]
FILES = sorted((ROOT / "fixtures" / "temporal").glob("*.json"))


def test_temporal_fixtures_present():
    assert {p.stem for p in FILES} >= {"sc-03-durable", "sc-10-unattested"}


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_temporal_fixture(path: Path):
    fx = json.loads(path.read_text(encoding="utf-8"))
    tl, exp = fx["timeline"], fx["expected"]
    validate_timeline_document(tl)
    steps = evaluate_timeline(tl)
    assert [sorted(f.agent_id for f in s["findings"] if f.violation) for s in steps] == exp["temporal_violations_by_step"]
    if "temporal_near_miss_by_step" in exp:
        assert [sorted(f.agent_id for f in s["findings"] if f.near_miss) for s in steps] == exp["temporal_near_miss_by_step"]
    if "static_violations_by_step" in exp:
        static = [sorted(f.agent_id for f in evaluate(document_to_lgraph(s["topology"])) if f.violation) for s in tl["steps"]]
        assert static == exp["static_violations_by_step"]


def test_packaged_timeline_schema_matches_repository():
    assert (ROOT / "mesa_ibi_scanner" / "data" / "mesa-timeline.schema.json").read_bytes() == (
        ROOT / "schemas" / "v0.2" / "mesa-timeline.schema.json").read_bytes()
