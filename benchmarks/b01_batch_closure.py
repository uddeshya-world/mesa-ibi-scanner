# SPDX-License-Identifier: Apache-2.0
"""B-01: batch closure and evaluation, 1,000 agents and 200 services. Target under 30 s.

Prints one JSON line. The generated estate is seeded (seed 7), so every run
measures the same graph. Timings vary by machine; evidence records pass/fail
against the target, not the raw number.

    python benchmarks/b01_batch_closure.py
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mesa_ibi_scanner.lattice import (
    FLOW_TYPES,
    LEdge,
    LGraph,
    LVertex,
    evaluate,
    frontier,
)

TARGET_S = 30.0
AGENTS, SERVICES, EDGES_PER_AGENT, SEED = 1000, 200, 6, 7
ZONES = ("research", "staging", "production", "regulated")


def estate() -> LGraph:
    rng = random.Random(SEED)
    g = LGraph()
    for i in range(AGENTS):
        g.add_vertex(LVertex(f"agent:{i}", "agent", (rng.choice((0, 0, 1)), 0, rng.choice((0, 1, 1, 2, 3))),
                             rng.choice(ZONES)))
    for i in range(SERVICES):
        g.add_vertex(LVertex(f"svc:{i}", "service", (rng.randint(0, 3), rng.randint(0, 3), 0)))
    for i in range(AGENTS):
        for _ in range(EDGES_PER_AGENT):
            s = f"svc:{rng.randrange(SERVICES)}"
            if rng.random() < 0.5:
                g.add_edge(LEdge(s, f"agent:{i}", "read", rng.random() < 0.1))
            else:
                g.add_edge(LEdge(f"agent:{i}", s, rng.choice(FLOW_TYPES), rng.random() < 0.1))
    return g


def main() -> int:
    g = estate()
    t0 = time.perf_counter()
    findings = evaluate(g)
    t_eval = time.perf_counter() - t0
    t1 = time.perf_counter()
    fr = frontier(g)
    t_frontier = time.perf_counter() - t1
    out = {
        "id": "B-01",
        "agents": AGENTS,
        "services": SERVICES,
        "edges": len(g.edges),
        "violations": sum(1 for f in findings if f.violation),
        "evaluate_s": round(t_eval, 3),
        "frontier_s": round(t_frontier, 3),
        "frontier_entries": sum(len(a["inbound"]) + len(a["outbound"]) for a in fr["agents"].values()),
        "target_s": TARGET_S,
        "result": "pass" if t_eval < TARGET_S else "fail",
    }
    print(json.dumps(out, sort_keys=True))
    return 0 if out["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
