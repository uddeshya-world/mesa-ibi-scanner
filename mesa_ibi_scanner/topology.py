"""Load and validate MESA estate topology JSON (v0.1 boolean, v0.2 graded)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

from .graph import Edge, EstateGraph, Vertex, VertexKind

if TYPE_CHECKING:
    from .lattice import LGraph

PathLike = Union[str, Path]

_SCHEMA_REL = Path("schemas") / "v0.1" / "mesa-topology.schema.json"
_SCHEMA_V02_REL = Path("schemas") / "v0.2" / "mesa-topology.schema.json"


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


def schema_v02_path() -> Path:
    """Resolve the v0.2 (graded) topology schema next to the repo / install root."""
    here = Path(__file__).resolve().parent
    for p in (here.parent / _SCHEMA_V02_REL, here / "data" / "mesa-topology-v0.2.schema.json"):
        if p.is_file():
            return p
    raise TopologyError(f"v0.2 topology schema not found; expected at {here.parent / _SCHEMA_V02_REL}")


def _load_schema(version: str = "0.1.0") -> dict[str, Any]:
    path = schema_v02_path() if version == "0.2.0" else schema_path()
    return json.loads(path.read_text(encoding="utf-8"))


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

    version = doc.get("topology_version", "0.1.0") if isinstance(doc, dict) else "0.1.0"
    schema = _load_schema(version)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    if errors:
        lines: list[str] = ["topology schema validation failed:"]
        for err in errors:
            loc = ".".join(str(p) for p in err.absolute_path) or "(root)"
            lines.append(f"  - {loc}: {err.message}")
        raise TopologyError("\n".join(lines))


def document_to_graph(doc: dict[str, Any]) -> EstateGraph:
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
                pdp_gate=bool(raw.get("pdp_gate", False)),
                label=str(raw.get("label") or ""),
            )
        )
    return g


def read_document(path: PathLike) -> dict[str, Any]:
    """Read and validate a topology JSON file of either version."""
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
    return doc


def load_any(path: PathLike) -> LGraph:
    """Load a v0.1 or v0.2 topology as a lattice graph (v0.1 is auto-promoted)."""
    from .lattice import document_to_lgraph

    doc = read_document(path)
    try:
        return document_to_lgraph(doc)
    except (KeyError, ValueError) as exc:
        raise TopologyError(str(exc)) from exc


def load_topology(path: PathLike) -> EstateGraph:
    """Read, validate, and convert a v0.1 topology JSON file to EstateGraph."""
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
