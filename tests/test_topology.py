"""Topology JSON load / schema validation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mesa_ibi_scanner.fixtures import fixture_hf_like
from mesa_ibi_scanner.graph import FULL, compute_inbound_closure, evaluate_invariant
from mesa_ibi_scanner.topology import TopologyError, load_topology, validate_topology_document

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "schemas" / "examples" / "topology-hf-like.json"


def test_load_topology_hf_like_matches_fixture():
    g = load_topology(EXAMPLE)
    cl = compute_inbound_closure(g)
    assert cl["agent:eval-worker"] == FULL
    results = {r.agent_id: r for r in evaluate_invariant(g)}
    assert results["agent:eval-worker"].violation is True

    # Same structural outcome as the built-in fixture
    fix = fixture_hf_like(with_pdp=False)
    fix_cl = compute_inbound_closure(fix)
    assert fix_cl["agent:eval-worker"] == cl["agent:eval-worker"]


def test_invalid_topology_missing_w(tmp_path: Path):
    bad = {
        "vertices": [{"id": "agent:a", "kind": "agent"}],
        "edges": [],
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(TopologyError) as ei:
        load_topology(path)
    assert "schema validation failed" in str(ei.value)


def test_invalid_edge_unknown_vertex(tmp_path: Path):
    doc = {
        "topology_version": "0.1.0",
        "vertices": [{"id": "agent:a", "kind": "agent", "w": [1, 0, 0]}],
        "edges": [
            {
                "src": "svc:missing",
                "dst": "agent:a",
                "flow_type": "read",
                "pdp_gate": False,
            }
        ],
    }
    validate_topology_document(doc)  # schema OK
    path = tmp_path / "dangling.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(TopologyError, match="unknown vertex"):
        load_topology(path)


def test_w_must_be_three_ints(tmp_path: Path):
    doc = {
        "vertices": [{"id": "agent:a", "kind": "agent", "w": [1, 0]}],
        "edges": [],
    }
    path = tmp_path / "short-w.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(TopologyError):
        load_topology(path)
