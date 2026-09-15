"""CLI for MESA IBI scanner research prototype."""

from __future__ import annotations

import argparse
import json
import sys

from . import __label__, __version__
from .fixtures import FIXTURES
from .graph import evaluate_invariant


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "MESA-INV-01 Cl(b) research prototype — not production. "
            f"label={__label__}"
        )
    )
    parser.add_argument(
        "--fixture",
        choices=sorted(FIXTURES.keys()),
        default="hf_like",
        help="Toy fixture name (HF/DseWiki-shaped; not live scanning).",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args(argv)

    g = FIXTURES[args.fixture]()
    results = evaluate_invariant(g)

    if args.json:
        payload = {
            "version": __version__,
            "label": __label__,
            "fixture": args.fixture,
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
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"mesa-ibi-scanner {__version__} [{__label__}]")
        print(f"fixture: {args.fixture}")
        print("-" * 60)
        for r in results:
            flag = "VIOLATION" if r.violation else "ok"
            print(
                f"{r.agent_id}: Cl={r.cl} full={r.full_trifecta} "
                f"pdp_ok={r.pdp_on_all_contributing_paths} => {flag}"
            )
            print(f"  contributors: {sorted(r.contributing_vertex_ids)}")
        print("-" * 60)
        print("No exploit recipes. Flow typing is illustrative only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
