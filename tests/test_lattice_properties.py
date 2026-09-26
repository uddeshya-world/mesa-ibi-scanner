"""T2 property: graded lattice (docs/LATTICE.md), checked on generated graphs.

P-01 monotonicity, P-02 join laws, P-03 cap attenuation, P-04 gating
soundness, P-05 boolean compatibility, P-07 frontier correctness, P-10
determinism, P-11 witness validity, P-12 minimal-cut validity. Each runs
CASES generated cases (default 10,000; MESA_T2_CASES may lower it for local
runs only) from seed 7, against the naive oracle in lattice_reference.py.
"""

from __future__ import annotations

import json
import os
import random
from typing import Any

import lattice_reference as ref

from mesa_ibi_scanner.graph import (
    Edge,
    EstateGraph,
    Vertex,
    VertexKind,
    evaluate_invariant,
)
from mesa_ibi_scanner.lattice import (
    attenuate,
    closure,
    document_to_lgraph,
    evaluate,
    frontier,
    join,
    promote,
)

CASES = int(os.environ.get("MESA_T2_CASES", "10000"))
SEED = 7
ZONES = ("research", "staging", "production", "regulated")
TH = ref.thresholds()


def _levels(rng: random.Random) -> dict[str, int]:
    return {d: rng.choice((0, 0, 1, 2, 3)) for d in "PUE"}


def gen(rng: random.Random, max_v: int = 6, max_e: int = 10, gates: bool = True, caps: bool = True):
    n_a = rng.randint(1, 3)
    n_s = rng.randint(0, max_v - n_a)
    vertices: dict[str, dict[str, Any]] = {}
    for i in range(n_a):
        vertices[f"agent:{i}"] = {"kind": "agent", "levels": _levels(rng), "zone": rng.choice(ZONES)}
    for i in range(n_s):
        vertices[f"svc:{i}"] = {"kind": "service", "levels": _levels(rng)}
    ids = sorted(vertices)
    edges: list[dict[str, Any]] = []
    for _ in range(rng.randint(0, max_e)):
        s, d = rng.choice(ids), rng.choice(ids)
        if s == d:
            continue
        e: dict[str, Any] = {"src": s, "dst": d, "flow_type": rng.choice(ref.FLOWS)}
        if gates and rng.random() < 0.2:
            e["pdp_gate"] = True
        if caps and rng.random() < 0.15:
            e["cap"] = _levels(rng)
        edges.append(e)
    return vertices, edges


def doc(vertices, edges) -> dict[str, Any]:
    vs = []
    for vid in sorted(vertices):
        d = vertices[vid]
        item = {"id": vid, "kind": d["kind"], "levels": dict(d["levels"])}
        if "zone" in d:
            item["zone"] = d["zone"]
        vs.append(item)
    es = []
    for e in edges:
        item = {"src": e["src"], "dst": e["dst"], "flow_type": e["flow_type"], "pdp_gate": bool(e.get("pdp_gate"))}
        if e.get("cap"):
            item["cap"] = dict(e["cap"])
        es.append(item)
    return {"topology_version": "0.2.0", "vertices": vs, "edges": es}


def _ref_vertices(vertices):
    return {v: {**d, "levels": (d["levels"]["P"], d["levels"]["U"], d["levels"]["E"])} for v, d in vertices.items()}


def test_p01_monotonicity_adding_an_edge_never_lowers_closure():
    rng = random.Random(SEED)
    for _ in range(CASES):
        v, e = gen(rng)
        before = closure(document_to_lgraph(doc(v, e)))
        ids = sorted(v)
        extra = {"src": rng.choice(ids), "dst": rng.choice(ids), "flow_type": rng.choice(ref.FLOWS)}
        if extra["src"] == extra["dst"]:
            continue
        after = closure(document_to_lgraph(doc(v, e + [extra])))
        for vid in before:
            assert all(after[vid][i] >= before[vid][i] for i in range(3)), (vid, before[vid], after[vid])


def test_p02_join_laws():
    rng = random.Random(SEED + 1)
    for _ in range(CASES):
        a, b, c = (tuple(rng.randint(0, 3) for _ in range(3)) for _ in range(3))
        assert join(a, b) == join(b, a)
        assert join(join(a, b), c) == join(a, join(b, c))
        assert join(a, a) == a
        assert join(a, (0, 0, 0)) == a


def test_p03_attenuation_never_raises_a_level():
    rng = random.Random(SEED + 2)
    for _ in range(CASES):
        lv = tuple(rng.randint(0, 3) for _ in range(3))
        cap = tuple(rng.randint(0, 3) for _ in range(3))
        out = attenuate(lv, cap)
        assert all(out[i] <= lv[i] and out[i] <= cap[i] for i in range(3))


def test_p04_nothing_propagates_across_a_gated_edge():
    rng = random.Random(SEED + 3)
    for _ in range(CASES):
        v, e = gen(rng)
        gated = [dict(x, pdp_gate=True) for x in e]
        cl = closure(document_to_lgraph(doc(v, gated)))
        for vid, d in v.items():
            assert cl[vid] == (d["levels"]["P"], d["levels"]["U"], d["levels"]["E"])
        # And the engine agrees with the oracle on the mixed graph.
        assert closure(document_to_lgraph(doc(v, e))) == ref.closure(_ref_vertices(v), e)


def _random_boolean_graph(rng: random.Random) -> EstateGraph:
    g = EstateGraph()
    n = rng.randint(2, 7)
    for i in range(n):
        kind = VertexKind.AGENT if i < 2 or rng.random() < 0.4 else VertexKind.SERVICE
        g.add_vertex(Vertex(f"v:{i}", kind, w=(rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1))))
    ids = sorted(g.vertices)
    for _ in range(rng.randint(0, 10)):
        s, d = rng.choice(ids), rng.choice(ids)
        if s != d:
            g.add_edge(Edge(s, d, flow_type=rng.choice(ref.FLOWS), pdp_gate=rng.random() < 0.2))
    return g


def test_p05_boolean_compatibility_under_every_zone_threshold():
    from mesa_ibi_scanner.fixtures import FIXTURES

    graphs = [f() for _, f in sorted(FIXTURES.items())]
    rng = random.Random(SEED + 4)
    graphs += [_random_boolean_graph(rng) for _ in range(CASES)]
    for g in graphs:
        want = {r.agent_id: r.violation for r in evaluate_invariant(g)}
        lg = promote(g)
        for zone in ZONES:
            for vx in lg.vertices.values():
                if vx.kind == "agent":
                    vx.zone = zone
            got = {f.agent_id: f.violation for f in evaluate(lg)}
            assert got == want, (zone, want, got)


def test_p07_frontier_matches_full_recompute():
    rng = random.Random(SEED + 5)
    for _ in range(CASES):
        v, e = gen(rng, max_v=5, max_e=6)
        fr = frontier(document_to_lgraph(doc(v, e)))
        want = ref.brute_frontier(_ref_vertices(v), e, TH)
        for aid, w in want.items():
            got = fr["agents"][aid]
            assert {(x["surface"], x["flow_type"]) for x in got["inbound"]} == w["inbound"], aid
            assert {(x["surface"], x["flow_type"]) for x in got["outbound"]} == w["outbound"], aid


def test_p10_determinism_byte_identical_output_under_input_order():
    rng = random.Random(SEED + 6)
    for _ in range(CASES):
        v, e = gen(rng)
        d1 = doc(v, e)
        d2 = json.loads(json.dumps(d1))
        rng.shuffle(d2["vertices"])
        rng.shuffle(d2["edges"])
        g1, g2 = document_to_lgraph(d1), document_to_lgraph(d2)
        assert json.dumps(frontier(g1), sort_keys=True) == json.dumps(frontier(g2), sort_keys=True)
        f1 = [f.as_dict() for f in evaluate(g1)]
        f2 = [f.as_dict() for f in evaluate(g2)]
        assert json.dumps(f1, sort_keys=True) == json.dumps(f2, sort_keys=True)


def test_p11_witness_paths_exist_and_reproduce_the_closure():
    rng = random.Random(SEED + 7)
    for _ in range(CASES):
        v, e = gen(rng)
        rv = _ref_vertices(v)
        for f in evaluate(document_to_lgraph(doc(v, e))):
            if not f.violation:
                continue
            for i, dim in enumerate("PUE"):
                path = f.witness[dim]
                assert path[-1] == f.agent_id
                assert ref.path_valid(path, i, f.closure[i], rv, e), (dim, path)


def test_p12_minimal_cut_breaks_closure_and_no_proper_subset_does():
    rng = random.Random(SEED + 8)
    for _ in range(CASES):
        v, e = gen(rng, max_e=12)
        rv = _ref_vertices(v)
        for f in evaluate(document_to_lgraph(doc(v, e))):
            if not f.violation:
                continue
            if f.min_cut is None:
                # Own levels already meet the threshold: no edge cut can break it.
                t = TH[v[f.agent_id]["zone"]]
                own = rv[f.agent_id]["levels"]
                assert all(own[i] >= t[i] for i in range(3)), (own, t)
                continue
            assert ref.cut_breaks(f.min_cut, f.agent_id, rv, e, TH)
            if len(e) <= 12:
                for sub in ref.proper_subsets(f.min_cut):
                    assert not ref.cut_breaks(list(sub), f.agent_id, rv, e, TH), (f.min_cut, sub)
