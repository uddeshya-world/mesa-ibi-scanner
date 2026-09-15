"""Unit tests for Cl(b) fixpoint — research prototype (cut semantics)."""

from mesa_ibi_scanner.fixtures import (
    fixture_dsewiki_like,
    fixture_hf_like,
    fixture_local_full_trifecta_agent,
    fixture_multihop,
)
from mesa_ibi_scanner.graph import FULL, EstateGraph, Edge, Vertex, VertexKind, compute_inbound_closure, evaluate_invariant


def test_hf_like_ungated_violation():
    g = fixture_hf_like(with_pdp=False)
    cl = compute_inbound_closure(g)
    assert cl["agent:eval-worker"] == FULL
    results = {r.agent_id: r for r in evaluate_invariant(g)}
    assert results["agent:eval-worker"].violation is True


def test_hf_like_gated_no_violation():
    g = fixture_hf_like(with_pdp=True)
    results = {r.agent_id: r for r in evaluate_invariant(g)}
    assert results["agent:eval-worker"].full_trifecta is True
    assert results["agent:eval-worker"].violation is False


def test_slack_zero_weight_does_not_close():
    """Notify service with w=(0,0,0) must not add trifecta bits."""
    g = EstateGraph()
    g.add_vertex(Vertex("agent:eval-worker", VertexKind.AGENT, w=(1, 0, 0)))
    g.add_vertex(Vertex("svc:slack-notify", VertexKind.SERVICE, w=(0, 0, 0)))
    g.add_edge(Edge("svc:slack-notify", "agent:eval-worker", "read"))
    cl = compute_inbound_closure(g)
    assert cl["agent:eval-worker"] == (1, 0, 0)


def test_dsewiki_like_one_edge_closure():
    g = fixture_dsewiki_like(with_pdp=False)
    cl = compute_inbound_closure(g)
    assert cl["agent:sandbox-coder"] == FULL
    assert evaluate_invariant(g)[0].violation is True


def test_dsewiki_gated():
    g = fixture_dsewiki_like(with_pdp=True)
    assert evaluate_invariant(g)[0].violation is False


def test_local_full_agent():
    g = fixture_local_full_trifecta_agent()
    r = evaluate_invariant(g)[0]
    assert r.cl == FULL
    assert r.violation is True


def test_single_gate_on_only_path_satisfies_invariant():
    g = fixture_multihop(with_pdp=True)
    r = {x.agent_id: x.violation for x in evaluate_invariant(g)}
    assert r["agent:target"] is False


def test_same_graph_ungated_is_violation():
    g = fixture_multihop(with_pdp=False)
    r = {x.agent_id: x.violation for x in evaluate_invariant(g)}
    assert r["agent:target"] is True


def test_all_paths_have_pdp_removed():
    import mesa_ibi_scanner.graph as graph_mod
    assert not hasattr(graph_mod, "_all_paths_have_pdp")
