"""Unit tests for Cl(b) fixpoint — research prototype."""

from mesa_ibi_scanner.fixtures import (
    fixture_dsewiki_like,
    fixture_hf_like,
    fixture_local_full_trifecta_agent,
)
from mesa_ibi_scanner.graph import FULL, compute_inbound_closure, evaluate_invariant


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


def test_slack_does_not_alone_close():
    """Non-contributing notify edge must not be the reason for closure bits."""
    g = fixture_hf_like(with_pdp=False)
    # Remove registry edge contribution by marking registry non-contributing
    g.vertices["svc:artifact-registry"].contributes = False
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
