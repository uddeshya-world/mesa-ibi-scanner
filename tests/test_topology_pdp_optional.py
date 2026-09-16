"""pdp_gate is optional in topology JSON (default false)."""

from __future__ import annotations

import json
from pathlib import Path

from mesa_ibi_scanner.topology import load_topology


def test_omitted_pdp_gate_defaults_false(tmp_path: Path):
    payload = {
        "vertices": [
            {"id": "agent:a", "kind": "agent", "w": [1, 0, 0]},
            {"id": "svc:s", "kind": "service", "w": [0, 1, 1]},
        ],
        "edges": [
            {"src": "svc:s", "dst": "agent:a", "flow_type": "write"}
            # pdp_gate omitted
        ],
    }
    path = tmp_path / "topo.json"
    path.write_text(json.dumps(payload))
    g = load_topology(path)
    assert len(g.edges) == 1
    assert g.edges[0].pdp_gate is False
