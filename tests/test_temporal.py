"""T1 unit: temporal closure (docs/TEMPORAL.md), SC-03 and SC-10 shapes, CLI flag."""

from __future__ import annotations

import json

from mesa_ibi_scanner.cli import main
from mesa_ibi_scanner.temporal import evaluate_timeline


def snap(agent_levels, edges=(), window="unbounded", zone="production", extra=()):
    vertices = [{"id": "agent:a", "kind": "agent", "levels": agent_levels, "zone": zone, "memory_window": window}]
    vertices += [{"id": "svc:regulated", "kind": "service", "levels": {"P": 3, "U": 0, "E": 0}},
                 {"id": "svc:tickets", "kind": "service", "levels": {"P": 0, "U": 2, "E": 0}}]
    vertices += list(extra)
    return {"topology_version": "0.2.0", "vertices": vertices, "edges": list(edges)}


READ_REG = {"src": "svc:regulated", "dst": "agent:a", "flow_type": "read"}
READ_TIX = {"src": "svc:tickets", "dst": "agent:a", "flow_type": "read"}
NO_E = {"P": 0, "U": 0, "E": 0}
E3 = {"P": 0, "U": 0, "E": 3}


def sc03(window="unbounded"):
    return {"timeline_version": "0.1.0", "steps": [
        {"t": 1, "topology": snap(NO_E, [READ_REG, READ_TIX], window)},
        {"t": 2, "topology": snap(E3, [READ_TIX], window)},
    ]}


def by_step(result, agent="agent:a"):
    return [next(f for f in step["findings"] if f.agent_id == agent) for step in result]


def test_sc03_static_passes_temporal_violates():
    steps = by_step(evaluate_timeline(sc03()))
    assert [f.violation for f in steps] == [False, True]
    assert steps[1].closure == (3, 2, 3)


def test_sc03_stateless_agent_matches_static():
    steps = by_step(evaluate_timeline(sc03(window="1")))
    assert [f.violation for f in steps] == [False, False]


def test_session_window_resets_on_new_session():
    tl = sc03(window="session")
    tl["steps"][0]["sessions"] = {"agent:a": "s1"}
    tl["steps"][1]["sessions"] = {"agent:a": "s1"}
    assert by_step(evaluate_timeline(tl))[1].violation
    tl["steps"][1]["sessions"] = {"agent:a": "s2"}
    assert not by_step(evaluate_timeline(tl))[1].violation


def sc10(attested):
    return {"timeline_version": "0.1.0", "steps": [
        {"t": 1, "topology": snap({"P": 0, "U": 0, "E": 2}, [READ_REG])},
        {"t": 2, "topology": snap({"P": 0, "U": 0, "E": 2}, []),
         "wipes": [{"agent": "agent:a", "attested": attested, "source": "agent:a#tool-log" if not attested
                    else "k8s:pvc/agent-a-memory#deleted"}]},
    ]}


def test_sc10_unattested_wipe_does_not_reset_near_miss_persists():
    steps = by_step(evaluate_timeline(sc10(attested=False)))
    assert steps[0].near_miss and steps[1].near_miss
    assert steps[1].closure == (3, 0, 2)


def test_attested_wipe_resets():
    steps = by_step(evaluate_timeline(sc10(attested=True)))
    assert steps[1].closure == (0, 0, 2) and not steps[1].near_miss


def test_memory_flows_onward_through_writes():
    downstream = {"id": "agent:b", "kind": "agent", "levels": {"P": 0, "U": 2, "E": 3}, "zone": "production"}
    tl = {"timeline_version": "0.1.0", "steps": [
        {"t": 1, "topology": snap(NO_E, [READ_REG], extra=[downstream])},
        {"t": 2, "topology": snap(NO_E, [{"src": "agent:a", "dst": "agent:b", "flow_type": "write"}], extra=[downstream])},
    ]}
    b = by_step(evaluate_timeline(tl), "agent:b")
    assert not b[0].violation and b[1].violation


def test_cli_timeline_flag(tmp_path, capsys):
    p = tmp_path / "tl.json"
    p.write_text(json.dumps(sc03()))
    rc = main(["--timeline", str(p), "--format", "json", "--exit-code"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1 and out["mode"] == "temporal"
    assert [s["violation_count"] for s in out["steps"]] == [0, 1]
