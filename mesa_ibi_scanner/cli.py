"""CLI for MESA IBI scanner research prototype."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __label__, __version__
from .fixtures import FIXTURES
from .graph import evaluate_invariant
from .report import (
    format_json,
    format_lattice_json,
    format_lattice_sarif,
    format_lattice_text,
    format_sarif,
    format_text,
)
from .topology import TopologyError, document_to_graph, read_document


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "MESA-INV-01 Cl(b) research prototype — not production. "
            f"label={__label__}"
        )
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument(
        "--fixture",
        choices=sorted(FIXTURES.keys()),
        help="Toy fixture name (HF/DseWiki-shaped; not live scanning).",
    )
    src.add_argument(
        "--timeline",
        metavar="TIMELINE.json",
        help="Temporal closure over a timeline of snapshots (docs/TEMPORAL.md).",
    )
    src.add_argument(
        "--input",
        metavar="TOPOLOGY.json",
        help="Path to estate topology JSON (validated against mesa-topology.schema.json).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "sarif"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=argparse.SUPPRESS,  # backward-compatible alias for --format json
    )
    parser.add_argument(
        "--exit-code",
        action="store_true",
        help="Exit non-zero if any Invariant 1 violation is present.",
    )
    parser.add_argument(
        "--severity",
        choices=("error", "warning", "note"),
        default=None,
        help=(
            "Severity threshold stub (deferred): currently all violations are "
            "'error'. Flag accepted for CI forward-compat; filtering not applied yet."
        ),
    )
    parser.add_argument(
        "--lattice",
        action="store_true",
        help="Graded lattice evaluation (docs/LATTICE.md). Automatic for v0.2 input.",
    )
    parser.add_argument(
        "--frontier-out",
        metavar="FRONTIER.json",
        help="Write the per-agent closure frontier (implies lattice mode).",
    )
    parser.add_argument(
        "--sign-key",
        metavar="ED25519.pem",
        help="Sign the exported frontier with this Ed25519 private key (needs the 'sign' extra).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"mesa-ibi-scanner {__version__}",
    )
    return parser


def _run_timeline(args: argparse.Namespace) -> int:
    from .lattice import thresholds_sha256
    from .temporal import evaluate_timeline
    from .topology import validate_timeline_document

    try:
        doc = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
        validate_timeline_document(doc)
        steps = evaluate_timeline(doc)
    except (OSError, ValueError, KeyError, TopologyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    payload: dict[str, Any] = {
        "version": __version__,
        "label": __label__,
        "mode": "temporal",
        "timeline": str(args.timeline),
        "thresholds_sha256": thresholds_sha256(),
        "steps": [
            {
                "t": s["t"],
                "agents": [f.as_dict() for f in s["findings"]],
                "memory": {a: {"P": m[0], "U": m[1], "E": m[2]} for a, m in s["memory"].items()},
                "attested_wipes": s["attested_wipes"],
                "unattested_wipe_claims": s["unattested_wipe_claims"],
                "violation_count": sum(1 for f in s["findings"] if f.violation),
                "near_miss_count": sum(1 for f in s["findings"] if f.near_miss),
            }
            for s in steps
        ],
    }
    if args.format == "text":
        lines = [f"mesa-ibi-scanner {__version__} [{__label__}] temporal mode", f"timeline: {args.timeline}", "-" * 60]
        for s in payload["steps"]:
            for a in s["agents"]:
                c = a["closure"]
                flag = "INV01" if a["violation"] else ("NEAR_MISS " + ",".join(a["missing"]) if a["near_miss"] else "ok")
                lines.append(f"t={s['t']} {a['agent_id']} [{a['zone']}]: Cl=(P{c['P']},U{c['U']},E{c['E']}) => {flag}")
            for claim in s["unattested_wipe_claims"]:
                lines.append(f"t={s['t']} {claim}: wipe claimed but not attested; memory kept")
        print("\n".join(lines))
    else:
        print(json.dumps(payload, indent=2))
    if args.exit_code and any(s["violation_count"] for s in payload["steps"]):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.json:
        args.format = "json"

    if args.timeline is not None:
        return _run_timeline(args)

    if args.input is None and args.fixture is None:
        args.fixture = "hf_like"

    from .lattice import (
        document_to_lgraph,
        evaluate,
        frontier,
        promote,
        sign_frontier,
        thresholds_sha256,
    )

    lg = None
    try:
        if args.input is not None:
            doc = read_document(args.input)
            source = str(args.input)
            source_kind = "input"
            input_uri = Path(args.input).expanduser().resolve().as_uri()
            if args.lattice or args.frontier_out or doc.get("topology_version") == "0.2.0":
                lg = document_to_lgraph(doc)
            else:
                g = document_to_graph(doc)
        else:
            g = FIXTURES[args.fixture]()
            source = args.fixture
            source_kind = "fixture"
            input_uri = f"fixture://{args.fixture}"
            if args.lattice or args.frontier_out:
                lg = promote(g)
    except TopologyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 — surface load errors clearly
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if lg is not None:
        findings = evaluate(lg)
        sha = thresholds_sha256()
        if args.format == "json":
            print(format_lattice_json(findings, source=source, source_kind=source_kind, thresholds_sha256=sha))
        elif args.format == "sarif":
            print(format_lattice_sarif(findings, source=source, source_kind=source_kind, thresholds_sha256=sha,
                                       input_uri=input_uri))
        else:
            print(format_lattice_text(findings, source=source, source_kind=source_kind, thresholds_sha256=sha))
        if args.frontier_out:
            fr = frontier(lg)
            if args.sign_key:
                fr = sign_frontier(fr, Path(args.sign_key).read_bytes())
            Path(args.frontier_out).write_bytes((json.dumps(fr, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        if args.exit_code and any(f.violation for f in findings):
            return 1
        return 0

    results = evaluate_invariant(g)

    if args.format == "json":
        print(format_json(results, source=source, source_kind=source_kind))
    elif args.format == "sarif":
        print(
            format_sarif(
                results,
                source=source,
                source_kind=source_kind,
                input_uri=input_uri,
            )
        )
    else:
        print(format_text(results, source=source, source_kind=source_kind))

    # --severity is a stub: documented deferred filtering; no behavior change yet.
    _ = args.severity

    if args.exit_code and any(r.violation for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
