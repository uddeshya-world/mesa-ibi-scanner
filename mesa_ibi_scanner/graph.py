"""Graph model for MESA-INV-01 directed inbound trifecta closure.

Research prototype only. No exploit logic.

Invariant 1 (cut semantics): PDP-gated edges are removed; violation iff
closure over the residual graph is still (1,1,1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

PropertyVector = Tuple[int, int, int]  # (private_data, untrusted_content, external_communication)

ZERO: PropertyVector = (0, 0, 0)
FULL: PropertyVector = (1, 1, 1)

# Illustrative / uncalibrated — which bits may propagate across an edge of this flow_type.
# Documented in README; not an empirical FP model.
FLOW_MASK: Dict[str, PropertyVector] = {
    "write": (1, 1, 1),  # full state transfer
    "goal-message": (0, 1, 0),  # untrusted content / intent, not data or egress
    "proxy/egress": (0, 0, 1),  # reachability / egress capability only
    "identity-mint": (1, 0, 1),  # credential / identity capability
    "read": (1, 1, 0),  # data + content, not egress capability
}


def join(a: PropertyVector, b: PropertyVector) -> PropertyVector:
    return (a[0] | b[0], a[1] | b[1], a[2] | b[2])


def mask(vec: PropertyVector, m: PropertyVector) -> PropertyVector:
    return (vec[0] & m[0], vec[1] & m[1], vec[2] & m[2])


class VertexKind(str, Enum):
    AGENT = "agent"
    SERVICE = "service"


@dataclass
class Vertex:
    id: str
    kind: VertexKind
    w: PropertyVector = ZERO
    tags: Set[str] = field(default_factory=set)


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


def _flow_mask_for(flow_type: str) -> PropertyVector:
    return FLOW_MASK.get(flow_type, FULL)


def compute_inbound_closure(g: EstateGraph) -> Dict[str, PropertyVector]:
    """Reachability fixpoint with per-edge flow-type masks.

    Cl(b) joins masked upstream closures along inbound edges.
    Complexity: O(|V| · |E|) iterative propagation (this function only).
    """
    cl: Dict[str, PropertyVector] = {vid: v.w for vid, v in g.vertices.items()}
    inbound = g.inbound_adjacency()
    changed = True
    for _ in range(max(1, len(g.vertices))):
        if not changed:
            break
        changed = False
        for dst, edges_in in inbound.items():
            before = cl[dst]
            acc = before
            for e in edges_in:
                acc = join(acc, mask(cl[e.src], _flow_mask_for(e.flow_type)))
            if acc != before:
                cl[dst] = acc
                changed = True
    return cl


def _contributors_for_agent(
    agent_id: str,
    inbound: Dict[str, List[Edge]],
) -> Set[str]:
    """Vertices that reach agent_id (including itself), via reverse BFS.

    Callers must pass a precomputed inbound adjacency (hoisted once per evaluate).
    """
    seen: Set[str] = set()
    stack = [agent_id]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for e in inbound.get(cur, []):
            if e.src not in seen:
                stack.append(e.src)
    return seen


def evaluate_invariant(g: EstateGraph) -> List[ClosureResult]:
    """Cut semantics: gated edges removed; violation iff residual Cl is FULL.

    Complexity: O(|V|·|E|) for the two closures, plus O(|V|+|E|) BFS only for
    agents that violate (lazy contributors).
    """
    residual = EstateGraph(
        vertices=dict(g.vertices),
        edges=[e for e in g.edges if not e.pdp_gate],
    )
    cl_residual = compute_inbound_closure(residual)
    cl_full = compute_inbound_closure(g)
    inbound_residual = residual.inbound_adjacency()  # hoist once
    results: List[ClosureResult] = []
    for vid, v in g.vertices.items():
        if v.kind != VertexKind.AGENT:
            continue
        cl = cl_full[vid]
        residual_cl = cl_residual[vid]
        full = cl == FULL
        violation = residual_cl == FULL
        contrib = (
            _contributors_for_agent(vid, inbound_residual) if violation else set()
        )
        results.append(
            ClosureResult(
                agent_id=vid,
                cl=cl,
                full_trifecta=full,
                pdp_on_all_contributing_paths=residual_cl != FULL,
                violation=violation,
                contributing_vertex_ids=contrib,
            )
        )
    return results
