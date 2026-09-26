"""T3 golden: lattice fixtures under fixtures/lattice/ against their expected verdicts.

Each fixture is also cross-checked against the naive oracle.
"""

from __future__ import annotations

import json
from pathlib import Path

import lattice_reference as ref
import pytest

from mesa_ibi_scanner.lattice import document_to_lgraph, evaluate
from mesa_ibi_scanner.topology import validate_topology_document

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_FILES = sorted((ROOT / "fixtures" / "lattice").glob("*.json"))
TH = ref.thresholds()


def test_at_least_sixty_public_fixtures():
    assert len(FIXTURE_FILES) >= 60


@pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: p.stem)
def test_fixture(path: Path):
    fx = json.loads(path.read_text(encoding="utf-8"))
    doc = fx["topology"]
    validate_topology_document(doc)
    findings = evaluate(document_to_lgraph(doc))
    exp = fx["expected"]
    assert sorted(f.agent_id for f in findings if f.violation) == exp["violations"]
    if "near_miss" in exp:
        assert sorted(f.agent_id for f in findings if f.near_miss) == exp["near_miss"]
    for aid, cl in exp.get("closure", {}).items():
        got = next(f for f in findings if f.agent_id == aid)
        assert got.closure == (cl["P"], cl["U"], cl["E"])
    vertices = {x["id"]: {"kind": x["kind"], "zone": x.get("zone", "production"),
                          "levels": (x["levels"]["P"], x["levels"]["U"], x["levels"]["E"])} for x in doc["vertices"]}
    assert ref.violating(vertices, doc["edges"], TH) == set(exp["violations"])
