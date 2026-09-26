"""Deliberately simple reference implementation of docs/LATTICE.md.

Test-author code. Properties compare the production engine against this
full-recompute oracle. Keep it naive: no precomputation, no cleverness.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

DIMS = ("P", "U", "E")
CAPS = {
    "write": (3, 3, 3),
    "read": (3, 3, 0),
    "goal-message": (0, 3, 0),
    "proxy/egress": (0, 0, 3),
    "identity-mint": (3, 0, 3),
}
FLOWS = tuple(sorted(CAPS))
ROOT = Path(__file__).resolve().parents[1]


def thresholds() -> dict[str, tuple[int, int, int]]:
    doc = json.loads((ROOT / "thresholds" / "zones.json").read_text(encoding="utf-8"))
    return {z: (t["P"], t["U"], t["E"]) for z, t in doc["zones"].items()}


def cap_of(edge: dict[str, Any]) -> tuple[int, int, int]:
    c = CAPS.get(edge["flow_type"], (3, 3, 3))
    extra = edge.get("cap")
    if extra:
        c = (min(c[0], extra["P"]), min(c[1], extra["U"]), min(c[2], extra["E"]))
    return c


def closure(vertices: dict[str, dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, tuple[int, int, int]]:
    """Naive fixpoint over the residual graph."""
    cl = {v: tuple(d["levels"]) for v, d in vertices.items()}
    live = [e for e in edges if not e.get("pdp_gate")]
    while True:
        changed = False
        for e in live:
            c = cap_of(e)
            src = cl[e["src"]]
            dst = cl[e["dst"]]
            new = tuple(max(dst[i], min(src[i], c[i])) for i in range(3))
            if new != dst:
                cl[e["dst"]] = new
                changed = True
        if not changed:
            return cl  # type: ignore[return-value]


def violating(vertices: dict[str, dict[str, Any]], edges: list[dict[str, Any]], th: dict[str, tuple[int, int, int]]) -> set[str]:
    cl = closure(vertices, edges)
    out = set()
    for v, d in vertices.items():
        if d["kind"] != "agent":
            continue
        t = th[d.get("zone", "production")]
        if all(cl[v][i] >= t[i] for i in range(3)):
            out.add(v)
    return out


def near_miss(vertices, edges, th) -> set[str]:
    cl = closure(vertices, edges)
    out = set()
    for v, d in vertices.items():
        if d["kind"] != "agent":
            continue
        t = th[d.get("zone", "production")]
        if sum(1 for i in range(3) if cl[v][i] < t[i]) == 1:
            out.add(v)
    return out


def brute_frontier(vertices, edges, th) -> dict[str, dict[str, set[tuple[str, str]]]]:
    """For each agent: inbound/outbound (surface, flow) whose addition creates a new violation."""
    base = violating(vertices, edges, th)
    out: dict[str, dict[str, set[tuple[str, str]]]] = {}
    for a, d in vertices.items():
        if d["kind"] != "agent":
            continue
        inbound, outbound = set(), set()
        for s in vertices:
            if s == a:
                continue
            for f in FLOWS:
                if violating(vertices, edges + [{"src": s, "dst": a, "flow_type": f}], th) - base:
                    inbound.add((s, f))
                if violating(vertices, edges + [{"src": a, "dst": s, "flow_type": f}], th) - base:
                    outbound.add((s, f))
        out[a] = {"inbound": inbound, "outbound": outbound}
    return out


def path_valid(path: list[str], dim: int, level: int, vertices, edges) -> bool:
    """Path exists in the residual graph, starts at a vertex holding `level`, and every hop's cap allows it."""
    if not path or vertices[path[0]]["levels"][dim] < level:
        return False
    live = [e for e in edges if not e.get("pdp_gate")]
    for u, v in itertools.pairwise(path):
        if not any(e["src"] == u and e["dst"] == v and cap_of(e)[dim] >= level for e in live):
            return False
    return True


def cut_breaks(cut: list[dict[str, str]], agent: str, vertices, edges, th) -> bool:
    remaining = list(edges)
    for c in cut:
        for i, e in enumerate(remaining):
            same = (e["src"], e["dst"], e["flow_type"], e.get("cap")) == (c["src"], c["dst"], c["flow_type"], c.get("cap"))
            if same and not e.get("pdp_gate"):
                remaining = remaining[:i] + remaining[i + 1:]
                break
        else:
            return False
    return agent not in violating(vertices, remaining, th)


def proper_subsets(items: list[Any]):
    for r in range(len(items)):
        yield from itertools.combinations(items, r)
