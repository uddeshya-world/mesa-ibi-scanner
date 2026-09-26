"""CI-friendly report formats: text, JSON, minimal SARIF 2.1.0."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

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
) -> dict[str, Any]:
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
    input_uri: str | None = None,
) -> str:
    """Minimal valid SARIF 2.1.0 document; results contain INV-01 violations only."""
    uri = input_uri or source
    sarif_results: list[dict[str, Any]] = []
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


# --- graded lattice (v0.4, docs/LATTICE.md) ----------------------------------------

NEAR_MISS_RULE_ID = "MESA-INV-01-NEAR-MISS"


def lattice_payload(
    findings: Sequence[Any],
    *,
    source: str,
    source_kind: str,
    thresholds_sha256: str,
) -> dict[str, Any]:
    return {
        "version": __version__,
        "label": __label__,
        "mode": "lattice",
        source_kind: source,
        "thresholds_sha256": thresholds_sha256,
        "agents": [f.as_dict() for f in findings],
        "violation_count": sum(1 for f in findings if f.violation),
        "near_miss_count": sum(1 for f in findings if f.near_miss),
    }


def format_lattice_json(findings: Sequence[Any], *, source: str, source_kind: str, thresholds_sha256: str) -> str:
    return json.dumps(
        lattice_payload(findings, source=source, source_kind=source_kind, thresholds_sha256=thresholds_sha256),
        indent=2,
    )


def format_lattice_text(findings: Sequence[Any], *, source: str, source_kind: str, thresholds_sha256: str) -> str:
    lines = [
        f"mesa-ibi-scanner {__version__} [{__label__}] lattice mode",
        f"{source_kind}: {source}",
        f"thresholds sha256: {thresholds_sha256[:16]}",
        "-" * 60,
    ]
    for f in findings:
        flag = "INV01" if f.violation else ("NEAR_MISS " + ",".join(f.missing) if f.near_miss else "ok")
        c, t = f.closure, f.threshold
        lines.append(f"{f.agent_id} [{f.zone}]: Cl=(P{c[0]},U{c[1]},E{c[2]}) T=(P{t[0]},U{t[1]},E{t[2]}) => {flag}")
        if f.violation and f.witness:
            for dim in ("P", "U", "E"):
                lines.append(f"  witness {dim}: {' -> '.join(f.witness[dim])}")
            if f.min_cut:
                cut = "; ".join(f"{e['src']} -> {e['dst']} ({e['flow_type']})" for e in f.min_cut)
                lines.append(f"  minimal cut ({f.cut_dimension}): {cut}")
            else:
                lines.append("  minimal cut: none (own levels already meet the threshold)")
    lines.append("-" * 60)
    lines.append("No exploit recipes. Thresholds come from the protected thresholds file.")
    return "\n".join(lines)


def format_lattice_sarif(
    findings: Sequence[Any],
    *,
    source: str,
    source_kind: str,
    thresholds_sha256: str,
    input_uri: str | None = None,
) -> str:
    uri = input_uri or source
    results: list[dict[str, Any]] = []
    for f in findings:
        if not (f.violation or f.near_miss):
            continue
        rule = RULE_ID if f.violation else NEAR_MISS_RULE_ID
        c = f.closure
        if f.violation:
            text = f"MESA INV01 in zone {f.zone}: agent {f.agent_id} closure (P{c[0]},U{c[1]},E{c[2]}) meets the threshold."
        else:
            text = f"MESA near miss in zone {f.zone}: agent {f.agent_id} is short only on {f.missing[0]}."
        results.append({
            "ruleId": rule,
            "level": "error" if f.violation else "warning",
            "message": {"text": text},
            "properties": {**f.as_dict(), "source_kind": source_kind, "source": source,
                           "thresholds_sha256": thresholds_sha256},
            "locations": [{
                "physicalLocation": {"artifactLocation": {"uri": uri}, "region": {"startLine": 1}},
                "logicalLocations": [{"fullyQualifiedName": f.agent_id, "kind": "agent"}],
            }],
        })
    doc = {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "mesa-ibi-scanner",
                "version": __version__,
                "informationUri": "https://github.com/uddeshya-world/mesa-ibi-scanner",
                "rules": [
                    {"id": RULE_ID, "name": "EnsembleTrifectaClosure",
                     "shortDescription": {"text": "MESA INV01: graded residual closure meets the zone threshold"},
                     "defaultConfiguration": {"level": "error"}, "helpUri": "https://doi.org/10.5281/zenodo.22743175"},
                    {"id": NEAR_MISS_RULE_ID, "name": "EnsembleTrifectaNearMiss",
                     "shortDescription": {"text": "MESA near miss: one dimension short of the zone threshold"},
                     "defaultConfiguration": {"level": "warning"}},
                ],
            }},
            "results": results,
        }],
    }
    return json.dumps(doc, indent=2)
