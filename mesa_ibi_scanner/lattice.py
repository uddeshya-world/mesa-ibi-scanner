# SPDX-License-Identifier: Apache-2.0
"""Graded lattice closure, zones, witnesses, minimal cuts and the closure frontier.

Implements docs/LATTICE.md. Research prototype. Deterministic: the same
graph and thresholds give the same output regardless of input order.
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .graph import EstateGraph, VertexKind

Levels = tuple[int, int, int]
DIMS = ("P", "U", "E")
ZERO: Levels = (0, 0, 0)
TOP: Levels = (3, 3, 3)
ZONES = ("research", "staging", "production", "regulated")
WINDOWS = ("1", "session", "unbounded")
FRONTIER_SCHEMA = "mesa-frontier/0.1"

FLOW_CAP: dict[str, Levels] = {
    "write": (3, 3, 3),
    "read": (3, 3, 0),
    "goal-message": (0, 3, 0),
    "proxy/egress": (0, 0, 3),
    "identity-mint": (3, 0, 3),
}
FLOW_TYPES = tuple(sorted(FLOW_CAP))


def join(a: Levels, b: Levels) -> Levels:
    return (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))


def attenuate(lv: Levels, cap: Levels) -> Levels:
    return (min(lv[0], cap[0]), min(lv[1], cap[1]), min(lv[2], cap[2]))


def geq(a: Levels, b: Levels) -> bool:
    return a[0] >= b[0] and a[1] >= b[1] and a[2] >= b[2]


def as_levels(d: Any) -> Levels:
    if isinstance(d, dict):
        return (int(d.get("P", 0)), int(d.get("U", 0)), int(d.get("E", 0)))
    return (int(d[0]), int(d[1]), int(d[2]))


def levels_dict(lv: Levels) -> dict[str, int]:
    return {"P": lv[0], "U": lv[1], "E": lv[2]}


@dataclass
class LVertex:
    id: str
    kind: str  # agent | service
    levels: Levels = ZERO
    zone: str = "production"
    window: str = "1"
    tags: set[str] = field(default_factory=set)


@dataclass
class LEdge:
    src: str
    dst: str
    flow_type: str = "read"
    pdp_gate: bool = False
    cap: Levels | None = None
    label: str = ""

    def effective_cap(self) -> Levels:
        c = FLOW_CAP.get(self.flow_type, TOP)
        return attenuate(c, self.cap) if self.cap is not None else c

    def key(self) -> tuple[Any, ...]:
        # An explicit cap equal to TOP is a different edge from no cap: keep them distinct so order is total.
        return (self.src, self.dst, self.flow_type, self.pdp_gate, self.cap is not None, self.cap or TOP, self.label)

    def ref(self) -> dict[str, Any]:
        out: dict[str, Any] = {"src": self.src, "dst": self.dst, "flow_type": self.flow_type}
        if self.cap is not None:
            out["cap"] = levels_dict(self.cap)
        return out


@dataclass
class LGraph:
    vertices: dict[str, LVertex] = field(default_factory=dict)
    edges: list[LEdge] = field(default_factory=list)

    def add_vertex(self, v: LVertex) -> None:
        self.vertices[v.id] = v

    def add_edge(self, e: LEdge) -> None:
        if e.src not in self.vertices or e.dst not in self.vertices:
            raise KeyError(f"edge endpoints must exist: {e.src} -> {e.dst}")
        self.edges.append(e)

    def canonical(self) -> LGraph:
        g = LGraph()
        for vid in sorted(self.vertices):
            g.vertices[vid] = self.vertices[vid]
        g.edges = sorted(self.edges, key=LEdge.key)
        return g

    def residual(self) -> list[LEdge]:
        return [e for e in sorted(self.edges, key=LEdge.key) if not e.pdp_gate]

    def agents(self) -> list[str]:
        return [vid for vid in sorted(self.vertices) if self.vertices[vid].kind == "agent"]


# --- thresholds -----------------------------------------------------------------


def _data_file(*rel: str) -> Path:
    here = Path(__file__).resolve().parent
    for p in (here.parent.joinpath(*rel), here / "data" / rel[-1]):
        if p.is_file():
            return p
    raise FileNotFoundError("/".join(rel))


def thresholds_path() -> Path:
    return _data_file("thresholds", "zones.json")


def load_thresholds(path: Path | None = None) -> dict[str, Levels]:
    doc = json.loads((path or thresholds_path()).read_text(encoding="utf-8"))
    return {z: as_levels(t) for z, t in doc["zones"].items()}


def thresholds_sha256(path: Path | None = None) -> str:
    return hashlib.sha256((path or thresholds_path()).read_bytes()).hexdigest()


# --- construction -----------------------------------------------------------------


def promote(g: EstateGraph) -> LGraph:
    """v0.1 boolean graph to the lattice: bit 1 -> level 3, zone production, window 1."""
    out = LGraph()
    for vid in sorted(g.vertices):
        v = g.vertices[vid]
        kind = "agent" if v.kind == VertexKind.AGENT else "service"
        out.add_vertex(LVertex(vid, kind, (3 * v.w[0], 3 * v.w[1], 3 * v.w[2]), tags=set(v.tags)))
    for e in g.edges:
        out.add_edge(LEdge(e.src, e.dst, e.flow_type, bool(e.pdp_gate), None, e.label))
    return out.canonical()


def document_to_lgraph(doc: dict[str, Any]) -> LGraph:
    """Build a lattice graph from a v0.2 document, or promote a v0.1 document."""
    if doc.get("topology_version") != "0.2.0":
        from .topology import document_to_graph

        return promote(document_to_graph(doc))
    g = LGraph()
    for raw in doc["vertices"]:
        vid = raw["id"]
        if vid in g.vertices:
            raise ValueError(f"duplicate vertex id: {vid}")
        g.add_vertex(LVertex(
            id=vid,
            kind=raw["kind"],
            levels=as_levels(raw.get("levels", {})),
            zone=raw.get("zone", "production"),
            window=str(raw.get("memory_window", "1")),
            tags=set(raw.get("tags") or []),
        ))
    for raw in doc["edges"]:
        cap = as_levels(raw["cap"]) if raw.get("cap") else None
        g.add_edge(LEdge(raw["src"], raw["dst"], raw["flow_type"], bool(raw.get("pdp_gate", False)), cap,
                         str(raw.get("label") or "")))
    return g.canonical()


# --- closure ----------------------------------------------------------------------


def _out_adj(g: LGraph, edges: Iterable[LEdge]) -> dict[str, list[LEdge]]:
    adj: dict[str, list[LEdge]] = {vid: [] for vid in g.vertices}
    for e in edges:
        adj[e.src].append(e)
    return adj


def _propagate(cl: dict[str, Levels], out: dict[str, list[LEdge]], seeds: Iterable[str]) -> set[str]:
    queue = deque(sorted(set(seeds)))
    queued = set(queue)
    changed: set[str] = set()
    while queue:
        u = queue.popleft()
        queued.discard(u)
        for e in out.get(u, []):
            new = join(cl[e.dst], attenuate(cl[u], e.effective_cap()))
            if new != cl[e.dst]:
                cl[e.dst] = new
                changed.add(e.dst)
                if e.dst not in queued:
                    queue.append(e.dst)
                    queued.add(e.dst)
    return changed


def closure(g: LGraph) -> dict[str, Levels]:
    """Least fixpoint over the residual graph (gated edges removed)."""
    cl = {vid: v.levels for vid, v in g.vertices.items()}
    _propagate(cl, _out_adj(g, g.residual()), g.vertices)
    return cl


class IncrementalClosure:
    """Closure maintained under edge additions and removals (used by mesa-d; P-06)."""

    def __init__(self, g: LGraph) -> None:
        self.graph = LGraph(dict(g.vertices), list(g.edges))
        self._cl = closure(self.graph)
        self._out = _out_adj(self.graph, self.graph.residual())

    def closure(self) -> dict[str, Levels]:
        return dict(self._cl)

    def add_vertex(self, v: LVertex) -> None:
        if v.id not in self.graph.vertices:
            self.graph.add_vertex(v)
            self._cl[v.id] = v.levels
            self._out[v.id] = []

    def add_edge(self, src: str, dst: str, flow_type: str, pdp_gate: bool = False, cap: Levels | None = None) -> set[str]:
        e = LEdge(src, dst, flow_type, pdp_gate, cap)
        self.graph.add_edge(e)
        if pdp_gate:
            return set()
        self._out[src].append(e)
        new = join(self._cl[dst], attenuate(self._cl[src], e.effective_cap()))
        if new == self._cl[dst]:
            return set()
        self._cl[dst] = new
        return {dst} | _propagate(self._cl, self._out, [dst])

    def remove_edge(self, src: str, dst: str, flow_type: str) -> set[str]:
        for i, e in enumerate(self.graph.edges):
            if (e.src, e.dst, e.flow_type) == (src, dst, flow_type) and not e.pdp_gate:
                del self.graph.edges[i]
                break
        else:
            return set()
        self._out[src] = [x for x in self._out[src] if x is not e]
        # Reverse-cone recompute: reset everything forward-reachable from dst, then re-propagate.
        cone: set[str] = set()
        stack = [dst]
        while stack:
            u = stack.pop()
            if u in cone:
                continue
            cone.add(u)
            stack.extend(x.dst for x in self._out[u])
        before = {v: self._cl[v] for v in cone}
        for v in cone:
            self._cl[v] = self.graph.vertices[v].levels
        seeds = set(cone)
        for u, es in self._out.items():
            if u not in cone and any(x.dst in cone for x in es):
                seeds.add(u)
        _propagate(self._cl, self._out, seeds)
        return {v for v in cone if self._cl[v] != before[v]}


# --- findings ---------------------------------------------------------------------


@dataclass
class Finding:
    agent_id: str
    zone: str
    closure: Levels
    threshold: Levels
    violation: bool
    near_miss: bool
    missing: list[str]
    witness: dict[str, list[str]] | None = None
    min_cut: list[dict[str, str]] | None = None
    cut_dimension: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "zone": self.zone,
            "closure": levels_dict(self.closure),
            "threshold": levels_dict(self.threshold),
            "violation": self.violation,
            "near_miss": self.near_miss,
            "missing": list(self.missing),
            "witness": self.witness,
            "min_cut": self.min_cut,
            "cut_dimension": self.cut_dimension,
        }


def _in_adj(g: LGraph, edges: list[LEdge]) -> dict[str, list[LEdge]]:
    adj: dict[str, list[LEdge]] = {vid: [] for vid in g.vertices}
    for e in edges:
        adj[e.dst].append(e)
    return adj


def _witness(g: LGraph, inbound: dict[str, list[LEdge]], x: str, dim: int, level: int) -> list[str]:
    """Shortest path from a vertex holding `level` in `dim` to x along edges whose cap allows it."""
    if g.vertices[x].levels[dim] >= level:
        return [x]
    parent: dict[str, str | None] = {x: None}
    frontier_ = [x]
    while frontier_:
        nxt: list[str] = []
        for v in frontier_:
            for e in inbound[v]:
                if e.effective_cap()[dim] >= level and e.src not in parent:
                    parent[e.src] = v
                    nxt.append(e.src)
        nxt.sort()
        for u in nxt:
            if g.vertices[u].levels[dim] >= level:
                path = [u]
                while parent[path[-1]] is not None:
                    path.append(parent[path[-1]])  # type: ignore[arg-type]
                return path
        frontier_ = nxt
    raise AssertionError("closure level has no witness; engine invariant broken")


def _min_cut(g: LGraph, edges: list[LEdge], x: str, dim: int, t: int) -> list[LEdge]:
    """Minimum edge cut separating {u: level >= t} from x in the cap >= t subgraph (Edmonds-Karp)."""
    usable = [e for e in edges if e.effective_cap()[dim] >= t]
    sources = sorted(v for v, vx in g.vertices.items() if vx.levels[dim] >= t)
    SRC = "\0source"
    # arcs: (u, v, capacity, edge-or-None); residual via index pairs
    heads: dict[str, list[int]] = {}
    arcs: list[list[Any]] = []

    def arc(u: str, v: str, cap: int, e: LEdge | None) -> None:
        heads.setdefault(u, []).append(len(arcs))
        arcs.append([v, cap, e])
        heads.setdefault(v, []).append(len(arcs))
        arcs.append([u, 0, None])

    big = len(usable) + 1
    for s in sources:
        arc(SRC, s, big, None)
    for e in usable:
        arc(e.src, e.dst, 1, e)
    while True:
        prev: dict[str, int] = {}
        q = deque([SRC])
        seen = {SRC}
        while q and x not in seen:
            u = q.popleft()
            for ai in heads.get(u, []):
                v, cap, _ = arcs[ai]
                if cap > 0 and v not in seen:
                    seen.add(v)
                    prev[v] = ai
                    q.append(v)
        if x not in seen:
            break
        v = x
        while v != SRC:
            ai = prev[v]
            arcs[ai][1] -= 1
            arcs[ai ^ 1][1] += 1
            v = arcs[ai ^ 1][0]
    cut = []
    for ai in range(0, len(arcs), 2):
        v, cap, e = arcs[ai]
        u = arcs[ai + 1][0]
        if e is not None and u in seen and v not in seen:
            cut.append(e)
    return sorted(cut, key=LEdge.key)


def evaluate(g: LGraph, thresholds: dict[str, Levels] | None = None) -> list[Finding]:
    th = thresholds or load_thresholds()
    g = g.canonical()
    residual = g.residual()
    cl = closure(g)
    inbound = _in_adj(g, residual)
    out: list[Finding] = []
    for aid in g.agents():
        vx = g.vertices[aid]
        t = th[vx.zone]
        c = cl[aid]
        missing = [DIMS[i] for i in range(3) if c[i] < t[i]]
        f = Finding(aid, vx.zone, c, t, not missing, len(missing) == 1, missing)
        if f.violation:
            f.witness = {DIMS[i]: _witness(g, inbound, aid, i, c[i]) for i in range(3)}
            best: tuple[int, int, list[LEdge]] | None = None
            for i in range(3):
                if vx.levels[i] >= t[i]:
                    continue
                cut = _min_cut(g, residual, aid, i, t[i])
                if best is None or len(cut) < best[0]:
                    best = (len(cut), i, cut)
            if best is not None:
                f.min_cut = [e.ref() for e in best[2]]
                f.cut_dimension = DIMS[best[1]]
        out.append(f)
    return out


# --- frontier ---------------------------------------------------------------------


def _sccs(nodes: list[str], succ: dict[str, list[str]]) -> tuple[dict[str, int], list[list[str]]]:
    """Tarjan, iterative. A component is emitted after every component it reaches."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on: set[str] = set()
    stack: list[str] = []
    comp: dict[str, int] = {}
    comps: list[list[str]] = []
    counter = 0
    for root in nodes:
        if root in index:
            continue
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on.add(root)
        calls = [(root, iter(succ.get(root, [])))]
        while calls:
            v, it = calls[-1]
            descended = False
            for w in it:
                if w not in index:
                    index[w] = low[w] = counter
                    counter += 1
                    stack.append(w)
                    on.add(w)
                    calls.append((w, iter(succ.get(w, []))))
                    descended = True
                    break
                if w in on:
                    low[v] = min(low[v], index[w])
            if descended:
                continue
            calls.pop()
            if calls:
                parent = calls[-1][0]
                low[parent] = min(low[parent], low[v])
            if low[v] == index[v]:
                members = []
                while True:
                    w = stack.pop()
                    on.discard(w)
                    comp[w] = len(comps)
                    members.append(w)
                    if w == v:
                        break
                comps.append(members)
    return comp, comps


def _reach_bits(g: LGraph, edges: list[LEdge], dim: int, level: int, bit: dict[str, int]) -> dict[str, int]:
    """For each vertex v, the bitset of agents x with bottleneck_dim(v -> x) >= level (v reaches itself)."""
    nodes = sorted(g.vertices)
    succ: dict[str, list[str]] = {v: [] for v in nodes}
    for e in edges:
        if e.effective_cap()[dim] >= level:
            succ[e.src].append(e.dst)
    comp, comps = _sccs(nodes, succ)
    reach_c = [0] * len(comps)
    for ci, members in enumerate(comps):  # reverse topological: successors first
        acc = 0
        for m in members:
            acc |= bit.get(m, 0)
            for w in succ[m]:
                if comp[w] != ci:
                    acc |= reach_c[comp[w]]
        reach_c[ci] = acc
    return {v: reach_c[comp[v]] for v in nodes}


def _minimal(vectors: set[Levels]) -> list[Levels]:
    return sorted(r for r in vectors if not any(o != r and geq(r, o) for o in vectors))


def _canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def frontier(g: LGraph, thresholds: dict[str, Levels] | None = None) -> dict[str, Any]:
    th = thresholds or load_thresholds()
    g = g.canonical()
    residual = g.residual()
    cl = closure(g)
    agents = g.agents()
    bit = {a: 1 << i for i, a in enumerate(agents)}
    violating = {a for a in agents if geq(cl[a], th[g.vertices[a].zone])}
    # Requirement vector per non-violating agent, grouped.
    groups: dict[Levels, int] = {}
    for a in agents:
        if a in violating:
            continue
        t = th[g.vertices[a].zone]
        r: Levels = (t[0] if cl[a][0] < t[0] else 0, t[1] if cl[a][1] < t[1] else 0, t[2] if cl[a][2] < t[2] else 0)
        groups[r] = groups.get(r, 0) | bit[a]
    reach: dict[tuple[int, int], dict[str, int]] = {}
    for r in groups:
        for i in range(3):
            if r[i] > 0 and (i, r[i]) not in reach:
                reach[(i, r[i])] = _reach_bits(g, residual, i, r[i], bit)
    all_bits = (1 << len(agents)) - 1
    req: dict[str, list[Levels]] = {}
    for v in sorted(g.vertices):
        found: set[Levels] = set()
        for r, members in groups.items():
            acc = members
            for i in range(3):
                if r[i] > 0:
                    acc &= reach[(i, r[i])][v]
            if acc & all_bits:
                found.add(r)
        req[v] = _minimal(found)

    def meets(c: Levels, rs: list[Levels]) -> bool:
        return any(geq(c, r) for r in rs)

    agents_doc: dict[str, Any] = {}
    for a in agents:
        inbound, outbound = [], []
        for s in sorted(g.vertices):
            if s == a:
                continue
            for f in FLOW_TYPES:
                cap = FLOW_CAP[f]
                if meets(attenuate(cl[s], cap), req[a]):
                    inbound.append({"surface": s, "flow_type": f})
                if meets(attenuate(cl[a], cap), req[s]):
                    outbound.append({"surface": s, "flow_type": f})
        agents_doc[a] = {
            "zone": g.vertices[a].zone,
            "closure": levels_dict(cl[a]),
            "threshold": levels_dict(th[g.vertices[a].zone]),
            "violating_now": a in violating,
            "requirements": [levels_dict(r) for r in req[a]],
            "inbound": inbound,
            "outbound": outbound,
        }
    surfaces = {
        v: {"closure": levels_dict(cl[v]), "requirements": [levels_dict(r) for r in req[v]]}
        for v in sorted(g.vertices) if g.vertices[v].kind != "agent"
    }
    body = {
        "frontier_schema": FRONTIER_SCHEMA,
        "thresholds": {z: levels_dict(t) for z, t in sorted(th.items())},
        "flow_caps": {f: levels_dict(FLOW_CAP[f]) for f in FLOW_TYPES},
        "agents": agents_doc,
        "surfaces": surfaces,
    }
    body["frontier_version"] = "f-" + hashlib.sha256(_canonical_bytes(body)).hexdigest()[:16]
    return body


def frontier_contains(fr: dict[str, Any], agent: str, surface: str, direction: str, flow_type: str) -> bool:
    entry = fr.get("agents", {}).get(agent)
    if entry is None:
        return False
    return {"surface": surface, "flow_type": flow_type} in entry.get(direction, [])


def _unsigned(fr: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in fr.items() if k != "signature"}


def sign_frontier(fr: dict[str, Any], private_key_pem: bytes) -> dict[str, Any]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = serialization.load_pem_private_key(private_key_pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("frontier signing key must be Ed25519")
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    out = _unsigned(fr)
    out["signature"] = {
        "alg": "ed25519",
        "key_id": hashlib.sha256(pub).hexdigest()[:16],
        "sig": base64.b64encode(key.sign(_canonical_bytes(_unsigned(fr)))).decode("ascii"),
    }
    return out


def verify_frontier(fr: dict[str, Any], public_key_pem: bytes) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    sig = fr.get("signature") or {}
    if sig.get("alg") != "ed25519":
        return False
    key = serialization.load_pem_public_key(public_key_pem)
    if not isinstance(key, Ed25519PublicKey):
        return False
    body = _unsigned(fr)
    if body.get("frontier_version") != "f-" + hashlib.sha256(
            _canonical_bytes({k: v for k, v in body.items() if k != "frontier_version"})).hexdigest()[:16]:
        return False
    try:
        key.verify(base64.b64decode(sig.get("sig", "")), _canonical_bytes(body))
    except (InvalidSignature, ValueError):
        return False
    return True
