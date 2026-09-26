# SPDX-License-Identifier: Apache-2.0
"""Temporal closure over a timeline of snapshots (docs/TEMPORAL.md, property P-08).

Each agent carries the join of its past closures for as long as its memory
window lasts. Only attested wipes (observed by infrastructure) reset memory;
an agent's own claim does not.
"""

from __future__ import annotations

from typing import Any

from .lattice import (
    ZERO,
    Levels,
    LGraph,
    document_to_lgraph,
    evaluate,
    join,
    load_thresholds,
)


def _effective(g: LGraph, memory: dict[str, Levels]) -> LGraph:
    out = LGraph(dict(g.vertices), list(g.edges))
    for aid, m in memory.items():
        v = out.vertices.get(aid)
        if v is not None and v.kind == "agent":
            out.vertices[aid] = type(v)(v.id, v.kind, join(v.levels, m), v.zone, v.window, set(v.tags))
    return out


def evaluate_timeline(timeline: dict[str, Any], thresholds: dict[str, Levels] | None = None) -> list[dict[str, Any]]:
    th = thresholds or load_thresholds()
    history: dict[str, list[Levels]] = {}  # closures in the current memory run, per agent
    last_session: dict[str, Any] = {}
    out: list[dict[str, Any]] = []
    for step in timeline.get("steps", []):
        g = document_to_lgraph(step["topology"])
        sessions = step.get("sessions") or {}
        attested = sorted({w["agent"] for w in step.get("wipes") or [] if w.get("attested") is True})
        claimed = sorted({w["agent"] for w in step.get("wipes") or [] if w.get("attested") is not True})
        memory: dict[str, Levels] = {}
        for aid in g.agents():
            window = g.vertices[aid].window
            if aid in attested:
                history[aid] = []
            if window == "session":
                sid = sessions.get(aid)
                if aid in last_session and last_session[aid] != sid:
                    history[aid] = []
                last_session[aid] = sid
            if window == "1":
                history[aid] = []
            acc = ZERO
            for c in history.get(aid, []):
                acc = join(acc, c)
            memory[aid] = acc
        findings = evaluate(_effective(g, memory), th)
        for f in findings:
            history.setdefault(f.agent_id, []).append(f.closure)
        out.append({
            "t": step.get("t"),
            "findings": findings,
            "attested_wipes": attested,
            "unattested_wipe_claims": claimed,
            "memory": {aid: memory[aid] for aid in sorted(memory)},
        })
    return out
