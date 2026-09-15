"""Toy fixtures shaped like public composition lessons — not exploit recipes.

HF-like: shared package registry usable as blackboard + proxy.
DseWiki-like: public GET-mutable site supplying untrusted+egress at one vertex.
Multihop: single PDP cut on the only inbound path into the target.
"""

from __future__ import annotations

from .graph import EstateGraph, Edge, Vertex, VertexKind


def fixture_hf_like(*, with_pdp: bool = False) -> EstateGraph:
    """Artifactory-shaped shared service: untrusted content + egress/proxy.

    Agent holds private_data. Inbound edge from registry into agent completes
    Cl(b)=(1,1,1). Optional PDP gate on that edge satisfies Invariant 1 (cut).
    Slack notify has w=(0,0,0); flow mask alone keeps it from adding bits.
    """
    g = EstateGraph()
    g.add_vertex(
        Vertex(
            id="agent:eval-worker",
            kind=VertexKind.AGENT,
            w=(1, 0, 0),
            tags={"acm"},
        )
    )
    g.add_vertex(
        Vertex(
            id="svc:artifact-registry",
            kind=VertexKind.SERVICE,
            w=(0, 1, 1),
            tags={"blackboard-capable", "proxy-capable"},
        )
    )
    g.add_vertex(
        Vertex(
            id="svc:slack-notify",
            kind=VertexKind.SERVICE,
            w=(0, 0, 0),
            tags={"notification"},
        )
    )
    g.add_edge(
        Edge(
            src="svc:artifact-registry",
            dst="agent:eval-worker",
            flow_type="write",
            pdp_gate=with_pdp,
            label="registry-blackboard-inbound",
        )
    )
    g.add_edge(
        Edge(
            src="svc:slack-notify",
            dst="agent:eval-worker",
            flow_type="read",
            pdp_gate=False,
            label="zero-weight-notify",
        )
    )
    return g


def fixture_dsewiki_like(*, with_pdp: bool = False) -> EstateGraph:
    """Public GET-mutable wiki-shaped vertex: untrusted + egress at one service."""
    g = EstateGraph()
    g.add_vertex(
        Vertex(
            id="agent:sandbox-coder",
            kind=VertexKind.AGENT,
            w=(1, 0, 0),
            tags={"acm"},
        )
    )
    g.add_vertex(
        Vertex(
            id="svc:public-get-mutable-wiki",
            kind=VertexKind.SERVICE,
            w=(0, 1, 1),
            tags={"get-mutates", "public-schelling", "blackboard-capable"},
        )
    )
    g.add_edge(
        Edge(
            src="svc:public-get-mutable-wiki",
            dst="agent:sandbox-coder",
            flow_type="write",
            pdp_gate=with_pdp,
            label="wiki-inbound",
        )
    )
    return g


def fixture_local_full_trifecta_agent() -> EstateGraph:
    """Per-agent Rule of Two failure: one agent already holds (1,1,1) unsupervised."""
    g = EstateGraph()
    g.add_vertex(
        Vertex(
            id="agent:overprivileged",
            kind=VertexKind.AGENT,
            w=(1, 1, 1),
            tags={"acm"},
        )
    )
    return g


def fixture_multihop(*, with_pdp: bool = True) -> EstateGraph:
    """Four-vertex chain; optional PDP on the only inbound path into target."""
    g = EstateGraph()
    g.add_vertex(Vertex("svc:untrusted-feed", VertexKind.SERVICE, w=(0, 1, 0)))
    g.add_vertex(Vertex("agent:relay", VertexKind.AGENT, w=(0, 0, 1)))
    g.add_vertex(Vertex("svc:board", VertexKind.SERVICE, w=(0, 0, 0)))
    g.add_vertex(Vertex("agent:target", VertexKind.AGENT, w=(1, 0, 0)))
    g.add_edge(Edge("svc:untrusted-feed", "agent:relay", "read"))
    g.add_edge(Edge("agent:relay", "svc:board", "write"))
    g.add_edge(
        Edge("svc:board", "agent:target", "write", pdp_gate=with_pdp, label="board-to-target")
    )
    return g


FIXTURES = {
    "hf_like": lambda: fixture_hf_like(with_pdp=False),
    "hf_like_gated": lambda: fixture_hf_like(with_pdp=True),
    "dsewiki_like": lambda: fixture_dsewiki_like(with_pdp=False),
    "dsewiki_like_gated": lambda: fixture_dsewiki_like(with_pdp=True),
    "local_full": fixture_local_full_trifecta_agent,
    "multihop_gated": lambda: fixture_multihop(with_pdp=True),
    "multihop_open": lambda: fixture_multihop(with_pdp=False),
}
