"""CLI for MESA IBI scanner research prototype."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.json:
        args.format = "json"

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
