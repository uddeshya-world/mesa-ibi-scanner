"""Load and validate MESA estate topology JSON (v0.1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from .graph import Edge, EstateGraph, Vertex, VertexKind

PathLike = Union[str, Path]

_SCHEMA_REL = Path("schemas") / "v0.1" / "mesa-topology.schema.json"


class TopologyError(ValueError):
    """Raised when topology JSON fails schema or referential checks."""


def schema_path() -> Path:
    """Resolve mesa-topology.schema.json next to the repo / install root."""
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / _SCHEMA_REL,
        here / "data" / "mesa-topology.schema.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise TopologyError(
        "mesa-topology.schema.json not found; expected at "
        f"{here.parent / _SCHEMA_REL}"
    )


def _load_schema() -> Dict[str, Any]:
    return json.loads(schema_path().read_text(encoding="utf-8"))


def validate_topology_document(doc: Any) -> None:
    """Validate *doc* against the topology schema; raise TopologyError on failure."""
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - dependency declared in pyproject
        raise TopologyError(
            "jsonschema is required to validate topology input; "
            "install mesa-ibi-scanner with its dependencies"
        ) from exc

    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    if errors:
        lines: List[str] = ["topology schema validation failed:"]
        for err in errors:
            loc = ".".join(str(p) for p in err.absolute_path) or "(root)"
            lines.append(f"  - {loc}: {err.message}")
        raise TopologyError("\n".join(lines))


def document_to_graph(doc: Dict[str, Any]) -> EstateGraph:
    """Build an EstateGraph from a validated topology document."""
    g = EstateGraph()
    seen: set[str] = set()
    for raw in doc["vertices"]:
        vid = raw["id"]
        if vid in seen:
            raise TopologyError(f"duplicate vertex id: {vid}")
        seen.add(vid)
        tags = set(raw.get("tags") or [])
        w = tuple(raw["w"])
        if len(w) != 3:
            raise TopologyError(f"vertex {vid}: w must be a 3-int array")
        g.add_vertex(
            Vertex(
                id=vid,
                kind=VertexKind(raw["kind"]),
                w=(int(w[0]), int(w[1]), int(w[2])),
                tags=tags,
            )
        )

    for raw in doc["edges"]:
        src, dst = raw["src"], raw["dst"]
        if src not in g.vertices:
            raise TopologyError(f"edge src unknown vertex: {src}")
        if dst not in g.vertices:
            raise TopologyError(f"edge dst unknown vertex: {dst}")
        g.add_edge(
            Edge(
                src=src,
                dst=dst,
                flow_type=raw["flow_type"],
                pdp_gate=bool(raw["pdp_gate"]),
                label=str(raw.get("label") or ""),
            )
        )
    return g


def load_topology(path: PathLike) -> EstateGraph:
    """Read, validate, and convert a topology JSON file to EstateGraph."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise TopologyError(f"cannot read topology file: {p}: {exc}") from exc
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TopologyError(f"invalid JSON in {p}: {exc}") from exc
    if not isinstance(doc, dict):
        raise TopologyError(f"topology root must be an object, got {type(doc).__name__}")
    validate_topology_document(doc)
    return document_to_graph(doc)
