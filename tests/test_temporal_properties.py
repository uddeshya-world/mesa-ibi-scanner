"""T2 property P-08: temporal closure on generated timelines (10,000 cases, seed 7)."""

from __future__ import annotations

import copy
import os
import random
from typing import Any

from test_lattice_properties import doc, gen

from mesa_ibi_scanner.lattice import document_to_lgraph, evaluate
from mesa_ibi_scanner.temporal import evaluate_timeline

CASES = int(os.environ.get("MESA_T2_CASES", "10000"))
SEED = 7


def timeline(rng: random.Random, window: str | None = None):
    v, _ = gen(rng)
    steps = []
    for t in range(rng.randint(1, 4)):
        _, e = gen(rng)
        vs = copy.deepcopy(v)
        for x in vs.values():
            if x["kind"] == "agent":
                x["levels"] = {d: rng.choice((0, 0, 1, 2, 3)) for d in "PUE"}
        d = doc(vs, [x for x in e if x["src"] in vs and x["dst"] in vs])
        for x in d["vertices"]:
            if x["kind"] == "agent":
                x["memory_window"] = window or rng.choice(("1", "session", "unbounded"))
        step: dict[str, Any] = {"t": t + 1, "topology": d, "sessions": {}, "wipes": []}
        for x in d["vertices"]:
            if x["kind"] == "agent":
                step["sessions"][x["id"]] = rng.choice(("s1", "s2"))
                if rng.random() < 0.2:
                    step["wipes"].append({"agent": x["id"], "attested": rng.random() < 0.5, "source": "test"})
        steps.append(step)
    return {"timeline_version": "0.1.0", "steps": steps}


def static(step):
    return {f.agent_id: f for f in evaluate(document_to_lgraph(step["topology"]))}


def test_p08_w1_equals_static():
    rng = random.Random(SEED)
    for _ in range(CASES):
        tl = timeline(rng, window="1")
        for step, res in zip(tl["steps"], evaluate_timeline(tl)):
            st = static(step)
            for f in res["findings"]:
                assert f.closure == st[f.agent_id].closure and f.violation == st[f.agent_id].violation


def test_p08_unbounded_at_least_static():
    rng = random.Random(SEED + 1)
    for _ in range(CASES):
        tl = timeline(rng, window="unbounded")
        for step, res in zip(tl["steps"], evaluate_timeline(tl)):
            st = static(step)
            for f in res["findings"]:
                assert all(f.closure[i] >= st[f.agent_id].closure[i] for i in range(3))


def test_p08_attested_wipe_resets_to_the_timeline_starting_there():
    rng = random.Random(SEED + 2)
    checked = 0
    for _ in range(CASES):
        tl = timeline(rng, window="unbounded")
        if len(tl["steps"]) < 2:
            continue
        k = rng.randrange(1, len(tl["steps"]))
        agents = [x["id"] for x in tl["steps"][k]["topology"]["vertices"] if x["kind"] == "agent"]
        for s in tl["steps"]:
            s["wipes"] = [w for w in s["wipes"] if not w["attested"]]
        tl["steps"][k]["wipes"] = [{"agent": a, "attested": True, "source": "infra"} for a in agents]
        full = evaluate_timeline(tl)
        tail = evaluate_timeline({"timeline_version": "0.1.0", "steps": tl["steps"][k:]})
        for a, b in zip(full[k:], tail):
            assert [(f.agent_id, f.closure) for f in a["findings"]] == [(f.agent_id, f.closure) for f in b["findings"]]
        checked += 1
    assert checked


def test_p08_unattested_wipe_changes_nothing():
    rng = random.Random(SEED + 3)
    for _ in range(CASES):
        tl = timeline(rng)
        for s in tl["steps"]:
            s["wipes"] = [w for w in s["wipes"] if not w["attested"]]
        with_claims = evaluate_timeline(tl)
        for s in tl["steps"]:
            s["wipes"] = []
        without = evaluate_timeline(tl)
        for a, b in zip(with_claims, without):
            assert [(f.agent_id, f.closure) for f in a["findings"]] == [(f.agent_id, f.closure) for f in b["findings"]]
