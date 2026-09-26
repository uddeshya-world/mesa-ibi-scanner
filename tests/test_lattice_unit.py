"""T1 unit: lattice primitives, schema v0.2, promotion, frontier export and signing, CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mesa_ibi_scanner.cli import main
from mesa_ibi_scanner.fixtures import FIXTURES
from mesa_ibi_scanner.lattice import (
    FLOW_CAP,
    IncrementalClosure,
    attenuate,
    closure,
    document_to_lgraph,
    evaluate,
    frontier,
    frontier_contains,
    load_thresholds,
    promote,
    sign_frontier,
    verify_frontier,
)
from mesa_ibi_scanner.topology import (
    TopologyError,
    load_any,
    validate_topology_document,
)

ROOT = Path(__file__).resolve().parents[1]


def v(vid, kind, P=0, U=0, E=0, zone=None):
    item = {"id": vid, "kind": kind, "levels": {"P": P, "U": U, "E": E}}
    if zone:
        item["zone"] = zone
    return item


def e(src, dst, flow, **kw):
    return {"src": src, "dst": dst, "flow_type": flow, **kw}


def topo(vertices, edges):
    return {"topology_version": "0.2.0", "vertices": vertices, "edges": edges}


def test_flow_caps_are_promoted_v01_masks():
    from mesa_ibi_scanner.graph import FLOW_MASK

    for flow, mask in FLOW_MASK.items():
        assert FLOW_CAP[flow] == tuple(3 * b for b in mask)


def test_attenuate_is_componentwise_min():
    assert attenuate((3, 2, 1), (1, 3, 0)) == (1, 2, 0)


def test_thresholds_file_loads_all_zones():
    th = load_thresholds()
    assert set(th) == {"research", "staging", "production", "regulated"}
    assert th["regulated"] == (1, 1, 1)


def test_schema_v02_validates_and_rejects_bad_levels():
    good = topo([v("agent:a", "agent", E=3, zone="regulated")], [])
    validate_topology_document(good)
    bad = topo([v("agent:a", "agent", P=4)], [])
    with pytest.raises(TopologyError):
        validate_topology_document(bad)


def test_v01_document_still_validates():
    validate_topology_document(json.loads((ROOT / "schemas" / "examples" / "topology-hf-like.json").read_text()))


def test_load_any_promotes_v01(tmp_path):
    g = load_any(ROOT / "schemas" / "examples" / "topology-hf-like.json")
    agent = g.vertices["agent:eval-worker"]
    assert agent.levels == (3, 0, 0) and agent.zone == "production"


def test_promote_maps_bits_to_level_3():
    lg = promote(FIXTURES["hf_like"]())
    assert lg.vertices["svc:artifact-registry"].levels == (0, 3, 3)


def test_graded_lattice_clears_mesh_internal_egress_in_production():
    d = topo(
        [v("agent:a", "agent", E=1), v("svc:cache", "service", P=2, U=1)],
        [e("svc:cache", "agent:a", "read")],
    )
    f = evaluate(document_to_lgraph(d))[0]
    assert f.closure == (2, 1, 1)
    assert not f.violation and not f.near_miss and f.missing == ["U", "E"]


def test_near_miss_when_exactly_one_dimension_is_short():
    d = topo([v("agent:a", "agent", E=2), v("svc:s", "service", P=3, U=1)], [e("svc:s", "agent:a", "read")])
    f = evaluate(document_to_lgraph(d))[0]
    assert f.near_miss and f.missing == ["U"] and not f.violation


def test_zone_changes_verdict():
    base = [v("svc:s", "service", P=1, U=1)]
    for zone, want in (("regulated", True), ("production", False)):
        d = topo([v("agent:a", "agent", E=1, zone=zone)] + base, [e("svc:s", "agent:a", "read")])
        assert evaluate(document_to_lgraph(d))[0].violation is want


def test_edge_cap_attenuates_obo_scoped_token_sc09():
    d = topo(
        [v("agent:orch", "agent", P=3, U=3), v("agent:worker", "agent", E=3)],
        [e("agent:orch", "agent:worker", "write", cap={"P": 1, "U": 3, "E": 3})],
    )
    worker = next(f for f in evaluate(document_to_lgraph(d)) if f.agent_id == "agent:worker")
    assert worker.closure == (1, 3, 3) and not worker.violation


def test_violation_has_witness_and_min_cut():
    d = topo(
        [v("agent:c", "agent", E=3), v("svc:data", "service", P=3), v("svc:queue", "service", U=2)],
        [e("svc:data", "agent:c", "read"), e("svc:queue", "agent:c", "read")],
    )
    f = evaluate(document_to_lgraph(d))[0]
    assert f.violation
    assert f.witness == {"P": ["svc:data", "agent:c"], "U": ["svc:queue", "agent:c"], "E": ["agent:c"]}
    assert f.min_cut == [{"src": "svc:data", "dst": "agent:c", "flow_type": "read"}]


def test_frontier_lists_closing_edge_and_requirements():
    d = topo([v("agent:c", "agent", P=3, E=3), v("svc:wiki", "service", U=3)], [])
    fr = frontier(document_to_lgraph(d))
    a = fr["agents"]["agent:c"]
    assert {"surface": "svc:wiki", "flow_type": "read"} in a["inbound"]
    assert {"P": 0, "U": 2, "E": 0} in a["requirements"]
    assert frontier_contains(fr, "agent:c", "svc:wiki", "inbound", "read")
    assert not frontier_contains(fr, "agent:c", "svc:wiki", "inbound", "proxy/egress")
    assert fr["frontier_version"].startswith("f-")


def test_frontier_signature_round_trip_and_tamper_detection():
    pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    priv = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    pub = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    fr = frontier(document_to_lgraph(topo([v("agent:c", "agent", P=3, E=3), v("svc:w", "service", U=3)], [])))
    signed = sign_frontier(fr, priv)
    assert verify_frontier(signed, pub)
    tampered = json.loads(json.dumps(signed))
    tampered["agents"]["agent:c"]["inbound"] = []
    assert not verify_frontier(tampered, pub)


def test_incremental_closure_equals_batch_after_adds_and_removes():
    d = topo(
        [v("agent:a", "agent", E=3), v("svc:s", "service", P=3), v("svc:t", "service", U=3)],
        [e("svc:s", "agent:a", "read")],
    )
    g = document_to_lgraph(d)
    inc = IncrementalClosure(g)
    inc.add_edge("svc:t", "svc:s", "write")
    assert inc.closure() == closure(inc.graph)
    inc.remove_edge("svc:t", "svc:s", "write")
    assert inc.closure() == closure(document_to_lgraph(d))


def test_cli_lattice_json_and_frontier_export(tmp_path, capsys):
    d = topo([v("agent:c", "agent", P=3, E=3), v("svc:w", "service", U=3)], [e("svc:w", "agent:c", "read")])
    p = tmp_path / "t.json"
    p.write_text(json.dumps(d))
    fr = tmp_path / "frontier.json"
    rc = main(["--input", str(p), "--format", "json", "--exit-code", "--frontier-out", str(fr)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1 and out["mode"] == "lattice" and out["violation_count"] == 1
    assert out["agents"][0]["witness"]["U"] == ["svc:w", "agent:c"]
    assert json.loads(fr.read_text())["frontier_schema"] == "mesa-frontier/0.1"


def test_cli_lattice_flag_on_v01_fixture(capsys):
    rc = main(["--fixture", "hf_like", "--lattice", "--format", "sarif", "--exit-code"])
    doc = json.loads(capsys.readouterr().out)
    assert rc == 1 and doc["runs"][0]["results"][0]["ruleId"] == "MESA-INV-01"


def test_cli_legacy_output_unchanged_without_lattice(capsys):
    main(["--fixture", "hf_like", "--format", "json"])
    out = json.loads(capsys.readouterr().out)
    assert "mode" not in out and out["agents"][0]["cl"] == [1, 1, 1]


def test_packaged_schemas_match_repository_schemas():
    pkg = ROOT / "mesa_ibi_scanner" / "data"
    for name, rel in (("mesa-topology.schema.json", "schemas/v0.1/mesa-topology.schema.json"),
                      ("mesa-topology-v0.2.schema.json", "schemas/v0.2/mesa-topology.schema.json"),
                      ("mesa-frontier.schema.json", "schemas/v0.2/mesa-frontier.schema.json"),
                      ("zones.json", "thresholds/zones.json")):
        assert (pkg / name).read_bytes() == (ROOT / rel).read_bytes(), name
