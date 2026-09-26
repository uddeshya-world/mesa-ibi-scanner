"""T1/T2: the upward-only advisory adapter (P-09, P-15; roadmap Section 12).

P-09: for any model output, including random, malformed and adversarial
ones, the final verdict is at least as strict as the deterministic verdict,
and no model can turn BLOCK or HOLD into ALLOW, or lower a level.
P-15: model timeout or error yields HOLD or BLOCK in production and
regulated zones.
"""

from __future__ import annotations

import os
import random

import pytest

from mesa_ibi_scanner.advisory import (
    QUESTIONS,
    Answer,
    JevAdapter,
    ModelError,
    NullModel,
    Verdict,
)

CASES = int(os.environ.get("MESA_T2_CASES", "10000"))
ZONES = ("research", "staging", "production", "regulated")


class ScriptedModel:
    """Returns whatever it is told to, including garbage, or raises."""

    version = "scripted-1"

    def __init__(self, behaviour):
        self.behaviour = behaviour

    def ask(self, question_id, payload):
        out = self.behaviour(question_id, payload)
        if isinstance(out, BaseException):
            raise out
        return out


GARBAGE = [
    Answer("ALLOW", 1.0, 5.0),
    Answer("allow", 0.99, 5.0),
    Answer("safe", 2.0, 5.0),
    Answer("yes", -1.0, 5.0),
    Answer("no", float("nan"), 5.0),
    Answer("yes", float("inf"), 5.0),
    Answer("", 0.5, 5.0),
    Answer("LOWER P TO 0", 1.0, 5.0),
    None,
    "ALLOW",
    {"label": "ALLOW"},
    42,
]


def _random_answer(rng):
    pick = rng.random()
    if pick < 0.3:
        return rng.choice(GARBAGE)
    if pick < 0.4:
        return rng.choice([ModelError("boom"), TimeoutError(), ValueError("x"), KeyError("k")])
    return Answer(rng.choice(["yes", "no"]), rng.random(), rng.uniform(1, 900))


def test_p09_final_verdict_never_less_strict_than_deterministic():
    rng = random.Random(7)
    for _ in range(CASES):
        det = rng.choice(list(Verdict))
        zone = rng.choice(ZONES)
        model = ScriptedModel(lambda q, p: _random_answer(rng))  # a fresh answer per question
        adapter = JevAdapter(model, timeout_ms=600)
        decision = adapter.decide(det, zone, {"tool": "t", "surface": "s"})
        assert decision.final >= det
        if det in (Verdict.BLOCK, Verdict.HOLD):
            assert decision.final != Verdict.ALLOW


def test_p09_level_proposals_only_raise():
    rng = random.Random(8)
    adapter = JevAdapter(NullModel())
    for _ in range(CASES):
        derived = rng.randint(0, 3)
        proposal = rng.choice([rng.randint(-5, 8), None, "3", 2.7, float("nan")])
        out = adapter.propose_level(derived, proposal)
        assert out >= derived and 0 <= out <= 3


@pytest.mark.parametrize("zone", ["production", "regulated"])
@pytest.mark.parametrize("failure", [ModelError("down"), TimeoutError(), RuntimeError("x")])
def test_p15_model_failure_fails_closed_in_production_and_regulated(zone, failure):
    adapter = JevAdapter(ScriptedModel(lambda q, p: failure))
    d = adapter.decide(Verdict.ALLOW, zone, {"tool": "t"})
    assert d.final in (Verdict.HOLD, Verdict.BLOCK)
    assert d.record["failure"] is not None


def test_research_zone_fails_open_with_a_logged_record():
    adapter = JevAdapter(ScriptedModel(lambda q, p: TimeoutError()))
    d = adapter.decide(Verdict.ALLOW, "research", {"tool": "t"})
    assert d.final == Verdict.ALLOW and d.record["failure"] == "TimeoutError"


def test_slow_answer_counts_as_timeout():
    adapter = JevAdapter(ScriptedModel(lambda q, p: Answer("no", 0.1, 5000.0)), timeout_ms=600)
    assert adapter.decide(Verdict.ALLOW, "production", {"tool": "t"}).final == Verdict.HOLD


def test_yes_above_threshold_on_irreversible_raises_to_hold():
    adapter = JevAdapter(ScriptedModel(lambda q, p: Answer("yes", 0.95, 50.0) if q == "irreversible" else Answer("no", 0.9, 50.0)))
    d = adapter.decide(Verdict.ALLOW, "production", {"tool": "t"})
    assert d.final == Verdict.HOLD


def test_injected_instruction_answer_can_block():
    adapter = JevAdapter(ScriptedModel(lambda q, p: Answer("yes", 0.99, 50.0) if q == "injected" else Answer("no", 0.9, 50.0)))
    assert adapter.decide(Verdict.ALLOW, "production", {"tool": "t"}).final == Verdict.BLOCK


def test_null_model_is_the_deterministic_verdict():
    adapter = JevAdapter(NullModel())
    for v in Verdict:
        for z in ZONES:
            assert adapter.decide(v, z, {"tool": "t"}).final == v


def test_payload_is_minimised_to_allowed_fields():
    seen = {}

    def capture(q, p):
        seen.update(p)
        return Answer("no", 0.1, 5.0)

    adapter = JevAdapter(ScriptedModel(capture))
    adapter.decide(Verdict.ALLOW, "production", {"tool": "t", "surface": "s", "credentials": "AKIA...", "arguments": {"x": 1}})
    assert "credentials" not in seen and "arguments" not in seen and seen["tool"] == "t"


def test_record_names_version_question_hash_and_threshold():
    adapter = JevAdapter(ScriptedModel(lambda q, p: Answer("no", 0.2, 12.0)))
    d = adapter.decide(Verdict.ALLOW, "production", {"tool": "t"})
    r = d.record
    assert r["model_version"] == "scripted-1"
    assert {a["question_id"] for a in r["answers"]} == set(QUESTIONS)
    assert all(len(a["wording_sha256"]) == 64 and "threshold" in a for a in r["answers"])


def test_deterministic_block_skips_the_model():
    calls = []
    adapter = JevAdapter(ScriptedModel(lambda q, p: calls.append(q) or Answer("no", 0.1, 1.0)))
    assert adapter.decide(Verdict.BLOCK, "production", {"tool": "t"}).final == Verdict.BLOCK
    assert calls == []
