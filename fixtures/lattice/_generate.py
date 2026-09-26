# SPDX-License-Identifier: Apache-2.0
"""Generate the lattice golden fixtures (test-author code).

Each fixture states every agent's closure by hand, from the family rules
below (a restatement of docs/LATTICE.md). Verdicts follow from those
closures and thresholds/zones.json by the INV01 and NEAR_MISS rules. Nothing
here calls the lattice engine. The boolean-era family takes its verdicts from
the v0.1 engine, which is the oracle for P-05. Run from the repository root:

    python fixtures/lattice/_generate.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from mesa_ibi_scanner.fixtures import FIXTURES
from mesa_ibi_scanner.graph import VertexKind, evaluate_invariant

OUT = ROOT / "fixtures" / "lattice"
ZONES = {z: (t["P"], t["U"], t["E"]) for z, t in json.loads((ROOT / "thresholds" / "zones.json").read_text())["zones"].items()}
CAPS = {"write": (3, 3, 3), "read": (3, 3, 0), "goal-message": (0, 3, 0), "proxy/egress": (0, 0, 3), "identity-mint": (3, 0, 3)}
DIMS = "PUE"

fixtures: list[dict] = []


def lv(c):
    return {"P": c[0], "U": c[1], "E": c[2]}


def vx(vid, kind, levels, zone=None):
    d = {"id": vid, "kind": kind, "levels": lv(levels)}
    if zone:
        d["zone"] = zone
    return d


def ed(src, dst, flow, gate=False, cap=None):
    d = {"src": src, "dst": dst, "flow_type": flow, "pdp_gate": gate}
    if cap:
        d["cap"] = lv(cap)
    return d


def add(fid, family, description, vertices, edges, closures):
    """closures: hand-stated closure for every agent vertex."""
    zones = {v["id"]: v.get("zone", "production") for v in vertices if v["kind"] == "agent"}
    assert set(zones) == set(closures), fid
    viol, near = [], []
    for aid, cl in closures.items():
        t = ZONES[zones[aid]]
        below = sum(1 for i in range(3) if cl[i] < t[i])
        if below == 0:
            viol.append(aid)
        elif below == 1:
            near.append(aid)
    doc = {"topology_version": "0.2.0", "vertices": vertices, "edges": edges}
    exp = {"violations": sorted(viol), "near_miss": sorted(near), "closure": {k: lv(c) for k, c in sorted(closures.items())}}
    fixtures.append({"id": fid, "family": family, "description": description, "topology": doc, "expected": exp})


# A. Level boundaries: exactly at the zone threshold, and one below on each dimension.
for zone, t in ZONES.items():
    add(f"boundary-{zone}-at", "boundary", f"closure equals the {zone} threshold",
        [vx("agent:a", "agent", (0, 0, t[2]), zone), vx("svc:s", "service", (t[0], t[1], 0))],
        [ed("svc:s", "agent:a", "read")], {"agent:a": t})
    for i, d in enumerate(DIMS):
        c = list(t)
        c[i] -= 1
        add(f"boundary-{zone}-{d}-below", "boundary", f"{d} one below the {zone} threshold",
            [vx("agent:a", "agent", (0, 0, c[2]), zone), vx("svc:s", "service", (c[0], c[1], 0))],
            [ed("svc:s", "agent:a", "read")], {"agent:a": tuple(c)})

# B. Flow caps: a (3,3,3) service into an agent that already holds E=3.
for zone in ZONES:
    for flow, cap in CAPS.items():
        add(f"flow-{zone}-{flow.replace('/', '-')}", "flow-cap", f"{flow} cap into an E=3 agent in {zone}",
            [vx("agent:a", "agent", (0, 0, 3), zone), vx("svc:s", "service", (3, 3, 3))],
            [ed("svc:s", "agent:a", flow)], {"agent:a": (cap[0], cap[1], 3)})

# C. Edge cap (SC-09, scoped on-behalf-of token): P attenuated to 1.
for zone in ZONES:
    add(f"edge-cap-{zone}", "edge-cap", f"orchestrator delegates with P capped at 1, {zone}",
        [vx("agent:orch", "agent", (3, 3, 0), "research"), vx("agent:worker", "agent", (0, 0, 3), zone)],
        [ed("agent:orch", "agent:worker", "write", cap=(1, 3, 3))],
        {"agent:orch": (3, 3, 0), "agent:worker": (1, 3, 3)})

# D. Gated edge: nothing crosses.
for zone, t in ZONES.items():
    add(f"gated-{zone}", "gated", f"the only inbound edge is PDP-gated, {zone}",
        [vx("agent:a", "agent", (0, 0, t[2]), zone), vx("svc:s", "service", (t[0], t[1], 0))],
        [ed("svc:s", "agent:a", "read", gate=True)], {"agent:a": (0, 0, t[2])})

# E. Multi-hop: goal-message carries only U; write carries everything.
for zone in ZONES:
    base = [vx("svc:s", "service", (3, 3, 3)), vx("agent:b", "agent", (0, 0, 0), "research"),
            vx("agent:a", "agent", (0, 0, 3), zone)]
    add(f"multihop-goal-{zone}", "multihop", f"read then goal-message: only U reaches the E=3 agent, {zone}",
        base, [ed("svc:s", "agent:b", "read"), ed("agent:b", "agent:a", "goal-message")],
        {"agent:a": (0, 3, 3), "agent:b": (3, 3, 0)})
    add(f"multihop-write-{zone}", "multihop", f"read then write: everything reaches the E=3 agent, {zone}",
        base, [ed("svc:s", "agent:b", "read"), ed("agent:b", "agent:a", "write")],
        {"agent:a": (3, 3, 3), "agent:b": (3, 3, 0)})

# F. Boolean-era fixtures (the paper cases), promoted, in every zone. Oracle: the v0.1 engine.
for name, factory in sorted(FIXTURES.items()):
    g = factory()
    want = sorted(r.agent_id for r in evaluate_invariant(g) if r.violation)
    for zone in ZONES:
        vertices = []
        for vid in sorted(g.vertices):
            x = g.vertices[vid]
            kind = "agent" if x.kind == VertexKind.AGENT else "service"
            vertices.append(vx(vid, kind, tuple(3 * b for b in x.w), zone if kind == "agent" else None))
        edges = [ed(e.src, e.dst, e.flow_type, e.pdp_gate) for e in g.edges]
        doc = {"topology_version": "0.2.0", "vertices": vertices, "edges": edges}
        fixtures.append({"id": f"v01-{name}-{zone}", "family": "boolean-era",
                         "description": f"v0.1 fixture {name} promoted, {zone}; verdict from the v0.1 engine",
                         "topology": doc, "expected": {"violations": want}})

for f in fixtures:
    (OUT / f"{f['id']}.json").write_bytes((json.dumps(f, indent=2, sort_keys=True) + "\n").encode("utf-8"))
print(f"wrote {len(fixtures)} fixtures")
