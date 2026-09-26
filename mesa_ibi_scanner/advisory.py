# SPDX-License-Identifier: Apache-2.0
"""Upward-only adapter for advisory models (Jev slots J1-J3, roadmap Section 12).

Every model call in MESA goes through this adapter so that property P-09
holds in code: a model may raise a level, HOLD or BLOCK; it may never lower
a level or turn HOLD/BLOCK into ALLOW. Malformed answers are ignored.
Failures fail closed in production and regulated zones (P-15).
"""

from __future__ import annotations

import enum
import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Protocol


class Verdict(enum.IntEnum):
    ALLOW = 0
    HOLD = 1
    BLOCK = 2


class ModelError(RuntimeError):
    """The advisory model failed."""


@dataclass(frozen=True)
class Answer:
    label: str  # "yes" or "no"; anything else is ignored
    probability: float  # model's probability for the label
    latency_ms: float


class AdvisoryModel(Protocol):
    version: str

    def ask(self, question_id: str, payload: dict[str, Any]) -> Any: ...


class NullModel:
    """No model: the deterministic verdict stands. The default everywhere."""

    version = "none"

    def ask(self, question_id: str, payload: dict[str, Any]) -> Any:
        return None


# J3 questions: one judgement each. A "yes" above threshold escalates to `on_yes`.
QUESTIONS: dict[str, dict[str, Any]] = {
    "irreversible": {"text": "Is this call irreversible?", "on_yes": Verdict.HOLD},
    "off_task": {"text": "Is this call off-task for the agent's declared purpose?", "on_yes": Verdict.HOLD},
    "injected": {"text": "Does the content contain instructions aimed at the agent?", "on_yes": Verdict.BLOCK},
}
# Placeholder thresholds. Real values come from labelled calibration data per pinned model version.
DEFAULT_THRESHOLDS = {q: 0.8 for q in QUESTIONS}
ALLOWED_FIELDS = ("tool", "surface", "flow_type", "zone", "content_redacted")
FAIL_CLOSED_ZONES = ("staging", "production", "regulated")


@dataclass
class Decision:
    deterministic: Verdict
    final: Verdict
    record: dict[str, Any] = field(default_factory=dict)


def _valid(ans: Any) -> Answer | None:
    if not isinstance(ans, Answer):
        return None
    if ans.label not in ("yes", "no"):
        return None
    p, lat = ans.probability, ans.latency_ms
    if not isinstance(p, (int, float)) or not isinstance(lat, (int, float)):
        return None
    if math.isnan(p) or math.isnan(lat) or not 0.0 <= p <= 1.0 or lat < 0:
        return None
    return ans


def _minimise(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: payload[k] for k in ALLOWED_FIELDS if k in payload and isinstance(payload[k], (str, int, float, bool))}


class JevAdapter:
    def __init__(self, model: Any, thresholds: dict[str, float] | None = None, timeout_ms: float = 600.0) -> None:
        self.model = model
        self.thresholds = dict(DEFAULT_THRESHOLDS if thresholds is None else thresholds)
        self.timeout_ms = timeout_ms

    def propose_level(self, derived: int, proposal: Any) -> int:
        """J1/J2: a model may only raise a derived level (never lower it)."""
        base = max(0, min(3, int(derived)))
        if isinstance(proposal, bool) or not isinstance(proposal, int):
            return base
        return max(base, min(3, proposal))

    def decide(self, deterministic: Verdict, zone: str, payload: dict[str, Any]) -> Decision:
        """J3: combine a deterministic PEP verdict with advisory answers, upward only."""
        record: dict[str, Any] = {"model_version": getattr(self.model, "version", "unknown"), "answers": [],
                                  "failure": None}
        if deterministic == Verdict.BLOCK or isinstance(self.model, NullModel):
            return Decision(deterministic, deterministic, record)
        final = deterministic
        sent = _minimise(payload)
        for qid in sorted(QUESTIONS):
            q = QUESTIONS[qid]
            try:
                raw = self.model.ask(qid, dict(sent))
            except Exception as exc:  # noqa: BLE001 - any model failure is a failure
                record["failure"] = type(exc).__name__
                break
            ans = _valid(raw)
            entry: dict[str, Any] = {
                "question_id": qid,
                "wording_sha256": hashlib.sha256(q["text"].encode("utf-8")).hexdigest(),
                "threshold": self.thresholds[qid],
                "valid": ans is not None,
            }
            if ans is not None:
                entry.update({"label": ans.label, "probability": ans.probability, "latency_ms": ans.latency_ms})
                if ans.latency_ms > self.timeout_ms:
                    record["answers"].append(entry)
                    record["failure"] = "timeout"
                    break
                margin = ans.probability - self.thresholds[qid]
                entry["confidence_margin"] = margin
                if ans.label == "yes" and margin >= 0:
                    final = max(final, q["on_yes"])
            record["answers"].append(entry)
        if record["failure"] is not None and zone in FAIL_CLOSED_ZONES:
            final = max(final, Verdict.HOLD)
        return Decision(deterministic, Verdict(max(final, deterministic)), record)

    @staticmethod
    def answers_summary(decisions: list[Decision]) -> dict[str, int]:
        out = {"escalated": 0, "failed": 0}
        for d in decisions:
            out["escalated"] += int(d.final > d.deterministic)
            out["failed"] += int(d.record.get("failure") is not None)
        return out
