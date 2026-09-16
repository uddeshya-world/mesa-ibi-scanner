"""Invariant property fuzz tests + perf regression — research prototype."""

from __future__ import annotations

import random
import time

from mesa_ibi_scanner.graph import (
    FULL,
    ZERO,
    Edge,
    EstateGraph,
    Vertex,
    VertexKind,
    compute_inbound_closure,
    evaluate_invariant,
    join,
)


FLOW_TYPES = ["write", "read", "goal-message", "proxy/egress", "identity-mint"]


def _rand_w(rng: random.Random):
    return (rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 1))


def _random_graph(rng: random.Random, n_agents: int = 8, n_services: int = 6, n_edges: int = 20) -> EstateGraph:
    g = EstateGraph()
    agents = [f"agent:{i}" for i in range(n_agents)]
    services = [f"svc:{i}" for i in range(n_services)]
    for a in agents:
        g.add_vertex(Vertex(a, VertexKind.AGENT, w=_rand_w(rng)))
    for s in services:
        g.add_vertex(Vertex(s, VertexKind.SERVICE, w=_rand_w(rng)))
    ids = agents + services
    for _ in range(n_edges):
        src, dst = rng.choice(ids), rng.choice(ids)
        if src == dst:
            continue
        g.add_edge(
            Edge(
                src,
                dst,
                flow_type=rng.choice(FLOW_TYPES),
                pdp_gate=rng.random() < 0.25,
            )
        )
    return g


def test_monotonicity_adding_ungated_edge_never_shrinks_cl():
    rng = random.Random(0)
    for i in range(40):
        g = _random_graph(rng)
        before = compute_inbound_closure(g)
        # add one ungated edge if possible
        ids = list(g.vertices)
        if len(ids) < 2:
            continue
        src, dst = rng.choice(ids), rng.choice(ids)
        if src == dst:
            continue
        g.add_edge(Edge(src, dst, flow_type="write", pdp_gate=False))
        after = compute_inbound_closure(g)
        for vid in before:
            b, a = before[vid], after[vid]
            assert a[0] >= b[0] and a[1] >= b[1] and a[2] >= b[2], (i, vid, b, a)


def test_gating_soundness_more_gates_never_creates_violation():
    rng = random.Random(1)
    for i in range(40):
        g = _random_graph(rng)
        base = {r.agent_id: r.violation for r in evaluate_invariant(g)}
        # gate every edge
        for e in g.edges:
            e.pdp_gate = True
        gated = {r.agent_id: r.violation for r in evaluate_invariant(g)}
        for aid, was in base.items():
            if gated[aid] and not was:
                raise AssertionError(f"gating created violation for {aid} on trial {i}")


def test_all_gated_only_locally_full_violates():
    rng = random.Random(2)
    for _ in range(40):
        g = _random_graph(rng)
        for e in g.edges:
            e.pdp_gate = True
        for r in evaluate_invariant(g):
            if r.violation:
                assert g.vertices[r.agent_id].w == FULL


def test_determinism_repeated_runs():
    rng = random.Random(3)
    g = _random_graph(rng, n_agents=12, n_services=10, n_edges=40)
    a = [(r.agent_id, r.cl, r.violation, frozenset(r.contributing_vertex_ids)) for r in evaluate_invariant(g)]
    b = [(r.agent_id, r.cl, r.violation, frozenset(r.contributing_vertex_ids)) for r in evaluate_invariant(g)]
    assert a == b


def test_perf_regression_2000_vertices_under_budget():
    """Pre-merge viability: 2k vertices should complete well under the old ~3s path."""
    rng = random.Random(42)
    n = 2000
    g = EstateGraph()
    for i in range(n):
        kind = VertexKind.AGENT if i % 3 == 0 else VertexKind.SERVICE
        g.add_vertex(Vertex(f"v:{i}", kind, w=_rand_w(rng)))
    ids = list(g.vertices)
    for _ in range(n * 3):
        src, dst = rng.choice(ids), rng.choice(ids)
        if src == dst:
            continue
        g.add_edge(Edge(src, dst, flow_type=rng.choice(FLOW_TYPES), pdp_gate=rng.random() < 0.2))
    t0 = time.perf_counter()
    results = evaluate_invariant(g)
    elapsed = time.perf_counter() - t0
    assert results, "expected some agents"
    # Budget: was ~3s pre-fix; allow CI slack
    assert elapsed < 8.0, f"evaluate_invariant too slow: {elapsed:.3f}s"
