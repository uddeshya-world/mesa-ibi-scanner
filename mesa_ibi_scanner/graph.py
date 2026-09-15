"""Graph model for MESA-INV-01 directed inbound trifecta closure.

Research prototype only. No exploit logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Set, Tuple

PropertyVector = Tuple[int, int, int]  # (private_data, untrusted_content, external_communication)


def join(a: PropertyVector, b: PropertyVector) -> PropertyVector:
    return (a[0] | b[0], a[1] | b[1], a[2] | b[2])


ZERO: PropertyVector = (0, 0, 0)
FULL: PropertyVector = (1, 1, 1)


class VertexKind(str, Enum):
    AGENT = "agent"
    SERVICE = "service"


@dataclass
class Vertex:
    id: str
    kind: VertexKind
    w: PropertyVector = ZERO
    tags: Set[str] = field(default_factory=set)
    # Flow-typing stub: if False, vertex does not contribute its w to closure
    contributes: bool = True


@dataclass
class Edge:
    src: str
    dst: str
    flow_type: str = "read"  # read | write | proxy/egress | identity-mint | goal-message
    pdp_gate: bool = False
    label: str = ""


@dataclass
class EstateGraph:
    """Directed interaction graph: edge src -> dst means influence/flow toward dst."""

    vertices: Dict[str, Vertex] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)

    def add_vertex(self, v: Vertex) -> None:
        self.vertices[v.id] = v

    def add_edge(self, e: Edge) -> None:
        if e.src not in self.vertices or e.dst not in self.vertices:
            raise KeyError(f"edge endpoints must exist: {e.src} -> {e.dst}")
        self.edges.append(e)

    def inbound_adjacency(self) -> Dict[str, List[Edge]]:
        adj: Dict[str, List[Edge]] = {vid: [] for vid in self.vertices}
        for e in self.edges:
            adj[e.dst].append(e)
        return adj


@dataclass
class ClosureResult:
    agent_id: str
    cl: PropertyVector
    full_trifecta: bool
    pdp_on_all_contributing_paths: bool
    violation: bool
    contributing_vertex_ids: Set[str]


def _vertex_contrib(v: Vertex) -> PropertyVector:
    return v.w if v.contributes else ZERO


def compute_inbound_closure(g: EstateGraph) -> Dict[str, PropertyVector]:
    """Reachability fixpoint: Cl(b) = OR of w(v) for all v that can reach b (incl. b).

    Complexity: O(|V| * |E|) style iterative propagation over reverse edges.
    """
    cl: Dict[str, PropertyVector] = {
        vid: _vertex_contrib(v) for vid, v in g.vertices.items()
    }
    inbound = g.inbound_adjacency()
    changed = True
    # Bound iterations by |V|; each pass may extend reachability one hop
    for _ in range(max(1, len(g.vertices))):
        if not changed:
            break
        changed = False
        for dst, edges_in in inbound.items():
            before = cl[dst]
            acc = before
            for e in edges_in:
                # Property flows along the edge toward dst (from src's closure)
                acc = join(acc, cl[e.src])
            if acc != before:
                cl[dst] = acc
                changed = True
    return cl


def _contributors_for_agent(g: EstateGraph, agent_id: str) -> Set[str]:
    """Vertices that reach agent_id (including itself), via reverse BFS."""
    inbound = g.inbound_adjacency()
    seen: Set[str] = set()
    stack = [agent_id]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for e in inbound[cur]:
            if e.src not in seen:
                stack.append(e.src)
    return seen


def _all_paths_have_pdp(g: EstateGraph, agent_id: str, contributors: Set[str]) -> bool:
    """Conservative check: every non-trivial inbound edge on the contributor subgraph
    that can carry a property into the agent must be PDP-gated for the invariant
    to hold when Cl=(1,1,1).

    For the prototype: if Cl is full, require that every edge whose src is in
    contributors and dst is in contributors ∪ {agent} leading toward the agent
    has pdp_gate=True on at least one edge on each simple path — approximated by
    requiring ALL inbound edges into the agent from the contributor set to be gated,
    OR a cut of gated edges separating external contributors. Simplified rule used
    here: every edge with dst==agent_id and src in contributors must have pdp_gate,
    AND if contributor services feed through intermediate agents, those edges too
    must be gated when they complete missing bits — for toy clarity we require
    pdp_gate on every edge in the contributor-induced inbound subgraph into agent.
    """
    if agent_id not in contributors:
        return True
    relevant = [
        e
        for e in g.edges
        if e.dst in contributors and e.src in contributors and e.dst != e.src
    ]
    # Edges that actually feed the agent or intermediate nodes on paths into agent
    if not relevant:
        # Only self-contribution: per-agent full trifecta still needs a gate on self use
        v = g.vertices[agent_id]
        return v.kind == VertexKind.AGENT and False  # unsupervised local full trifecta = violation
    return all(e.pdp_gate for e in relevant)


def evaluate_invariant(g: EstateGraph) -> List[ClosureResult]:
    """Flag agents with Cl(b)=(1,1,1) without PDP coverage on contributing paths."""
    closures = compute_inbound_closure(g)
    results: List[ClosureResult] = []
    for vid, v in g.vertices.items():
        if v.kind != VertexKind.AGENT:
            continue
        cl = closures[vid]
        full = cl == FULL
        contrib = _contributors_for_agent(g, vid)
        # Narrow contributors to those that supply at least one bit present in cl
        meaningful = {
            cid
            for cid in contrib
            if join(ZERO, _vertex_contrib(g.vertices[cid])) != ZERO
            or cid == vid
        }
        pdp_ok = True
        if full:
            pdp_ok = _all_paths_have_pdp(g, vid, meaningful)
            # Local unsupervised full trifecta on the agent alone
            if meaningful <= {vid} and _vertex_contrib(v) == FULL:
                pdp_ok = False
        violation = full and not pdp_ok
        results.append(
            ClosureResult(
                agent_id=vid,
                cl=cl,
                full_trifecta=full,
                pdp_on_all_contributing_paths=pdp_ok if full else True,
                violation=violation,
                contributing_vertex_ids=meaningful,
            )
        )
    return results
