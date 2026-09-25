"""CI-friendly report formats: text, JSON, minimal SARIF 2.1.0."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from . import __label__, __version__
from .graph import ClosureResult

SARIF_SCHEMA = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/"
    "master/Schemata/sarif-schema-2.1.0.json"
)
RULE_ID = "MESA-INV-01"


def results_payload(
    results: Sequence[ClosureResult],
    *,
    source: str,
    source_kind: str,
) -> Dict[str, Any]:
    return {
        "version": __version__,
        "label": __label__,
        source_kind: source,
        "agents": [
            {
                "agent_id": r.agent_id,
                "cl": list(r.cl),
                "full_trifecta": r.full_trifecta,
                "pdp_on_all_contributing_paths": r.pdp_on_all_contributing_paths,
                "violation": r.violation,
                "contributing_vertex_ids": sorted(r.contributing_vertex_ids),
            }
            for r in results
        ],
        "violation_count": sum(1 for r in results if r.violation),
    }


def format_text(
    results: Sequence[ClosureResult],
    *,
    source: str,
    source_kind: str,
) -> str:
    lines = [
        f"mesa-ibi-scanner {__version__} [{__label__}]",
        f"{source_kind}: {source}",
        "-" * 60,
    ]
    for r in results:
        flag = "VIOLATION" if r.violation else "ok"
        lines.append(
            f"{r.agent_id}: Cl={r.cl} full={r.full_trifecta} "
            f"pdp_ok={r.pdp_on_all_contributing_paths} => {flag}"
        )
        lines.append(f"  contributors: {sorted(r.contributing_vertex_ids)}")
    lines.append("-" * 60)
    lines.append("No exploit recipes. Flow typing is illustrative only.")
    return "\n".join(lines)


def format_json(
    results: Sequence[ClosureResult],
    *,
    source: str,
    source_kind: str,
) -> str:
    return json.dumps(
        results_payload(results, source=source, source_kind=source_kind),
        indent=2,
    )


def format_sarif(
    results: Sequence[ClosureResult],
    *,
    source: str,
    source_kind: str,
    input_uri: Optional[str] = None,
) -> str:
    """Minimal valid SARIF 2.1.0 document; results contain INV-01 violations only."""
    uri = input_uri or source
    sarif_results: List[Dict[str, Any]] = []
    for r in results:
        if not r.violation:
            continue
        message = (
            f"MESA Invariant 1 violation: agent {r.agent_id} has residual "
            f"Cl(b)=(1,1,1) (full trifecta after PDP cut). "
            f"Contributors: {sorted(r.contributing_vertex_ids)}"
        )
        sarif_results.append(
            {
                "ruleId": RULE_ID,
                "level": "error",
                "message": {"text": message},
                "properties": {
                    "agent_id": r.agent_id,
                    "cl": list(r.cl),
                    "source_kind": source_kind,
                    "source": source,
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": uri},
                            "region": {"startLine": 1},
                        },
                        "logicalLocations": [
                            {
                                "fullyQualifiedName": r.agent_id,
                                "kind": "agent",
                            }
                        ],
                    }
                ],
            }
        )

    doc = {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "mesa-ibi-scanner",
                        "version": __version__,
                        "informationUri": (
                            "https://github.com/uddeshya-world/mesa-ibi-scanner"
                        ),
                        "rules": [
                            {
                                "id": RULE_ID,
                                "name": "EnsembleTrifectaClosure",
                                "shortDescription": {
                                    "text": (
                                        "MESA Invariant 1: residual inbound "
                                        "trifecta closure Cl(b) must not be (1,1,1)"
                                    )
                                },
                                "fullDescription": {
                                    "text": (
                                        "PDP-gated edges are removed (cut semantics). "
                                        "Violation iff closure over the residual "
                                        "graph remains (private_data, untrusted_content, "
                                        "external_communication)=(1,1,1)."
                                    )
                                },
                                "defaultConfiguration": {"level": "error"},
                                "helpUri": "https://doi.org/10.5281/zenodo.22743175",
                            }
                        ],
                    }
                },
                "results": sarif_results,
            }
        ],
    }
    return json.dumps(doc, indent=2)
