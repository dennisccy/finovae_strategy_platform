"""Immutable hard cost tracker (iter-3 / J-13).

Invariants under test:
  * accumulated spend is monotonic / append-only (never decreases);
  * caps are fixed at construction (cannot be raised/lowered mid-run);
  * zero / negative / absent caps fall back to a safe finite default —
    still hard-bounded, NEVER unbounded;
  * ``would_exceed`` fires independently on the AI-token, USD,
    max-configs, and wall-clock caps;
  * ``snapshot`` is the durable, UI-renderable spend record.
"""

from __future__ import annotations

import dataclasses

import pytest

from backend.cost_tracker import (
    DEFAULT_MAX_AI_TOKENS,
    DEFAULT_MAX_USD,
    HARD_MAX_AI_TOKENS,
    HARD_MAX_USD,
    CostTracker,
)


class _FakeClock:
    """Deterministic monotonic clock so the wall-clock cap is non-flaky."""

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


# --- cap resolution ----------------------------------------------------------

def test_absent_or_nonpositive_caps_fall_back_to_safe_finite_default():
    t = CostTracker(max_ai_tokens=None, max_usd=0, max_configs=-3,
                    max_wall_clock_seconds=0)
    assert t.caps.max_ai_tokens == DEFAULT_MAX_AI_TOKENS
    assert t.caps.max_usd == DEFAULT_MAX_USD
    assert t.caps.max_configs >= 2  # open-universe needs ≥2 distinct configs
    # wall-clock unset → no wall cap (matches the pre-iter-3 semantics) but
    # the run is still hard-bounded by the finite token/usd/config caps.
    assert t.caps.max_wall_clock_seconds is None
    assert t.would_exceed() is None


def test_huge_caps_are_clamped_to_the_hard_ceiling_never_unbounded():
    t = CostTracker(max_ai_tokens=10**18, max_usd=10**9,
                    max_configs=10**6, max_wall_clock_seconds=10**12)
    assert t.caps.max_ai_tokens == HARD_MAX_AI_TOKENS
    assert t.caps.max_usd == HARD_MAX_USD
    assert t.caps.max_configs <= 64
    assert t.caps.max_wall_clock_seconds is not None


# --- immutability ------------------------------------------------------------

def test_caps_are_frozen_and_cannot_be_mutated_midrun():
    t = CostTracker(max_ai_tokens=100, max_usd=1.0, max_configs=2)
    caps = t.caps
    # The caps object is a frozen dataclass — a mid-run "raise the cap"
    # attempt must fail outright, never silently widen the budget.
    with pytest.raises(dataclasses.FrozenInstanceError):
        caps.max_ai_tokens = 10**9  # type: ignore[misc]
    # There is no public mutator that re-resolves caps, and the effective
    # cap is unchanged.
    assert t.caps.max_ai_tokens == 100
    assert not hasattr(t, "set_caps")


def test_spend_is_monotonic_and_negative_usage_is_ignored():
    t = CostTracker(max_ai_tokens=10_000, max_usd=100.0, max_configs=5)
    t.record_usage("gpt-5.4-mini", 100, 50)
    assert t.ai_tokens == 150
    usd_after_first = t.usd
    assert usd_after_first > 0.0
    # Negative / None token counts must NOT decrease the running totals.
    t.record_usage("gpt-5.4-mini", -1000, -1000)
    t.record_usage("gpt-5.4-mini", None, None)  # type: ignore[arg-type]
    assert t.ai_tokens == 150
    assert t.usd == usd_after_first
    # A further real call only ever increases the totals.
    t.record_usage("gpt-5.4-mini", 10, 10)
    assert t.ai_tokens == 170
    assert t.usd > usd_after_first


# --- independent per-cap enforcement -----------------------------------------

def test_token_cap_fires_independently():
    t = CostTracker(max_ai_tokens=200, max_usd=10**6, max_configs=10**3)
    assert t.would_exceed() is None
    t.record_usage("gpt-5.4-mini", 150, 60)  # 210 ≥ 200
    assert t.would_exceed() == "ai-tokens"


def test_usd_cap_fires_independently_even_below_token_cap():
    # Tiny USD cap; few tokens but priced over the USD ceiling.
    t = CostTracker(max_ai_tokens=10**9, max_usd=0.0005, max_configs=10**3)
    assert t.would_exceed() is None
    t.record_usage("gpt-5.4-mini", 1000, 1000)
    assert t.ai_tokens < t.caps.max_ai_tokens  # token cap NOT the trigger
    assert t.would_exceed() == "usd"


def test_max_configs_cap_fires_independently():
    t = CostTracker(max_ai_tokens=10**9, max_usd=10**6, max_configs=2)
    assert t.would_exceed() is None
    t.start_config()
    assert t.would_exceed() is None
    t.start_config()
    assert t.configs_run == 2
    assert t.would_exceed() == "max-configs"  # "no one more config past cap"


def test_wall_clock_cap_fires_independently_with_injected_clock():
    clk = _FakeClock()
    t = CostTracker(max_ai_tokens=10**9, max_usd=10**6, max_configs=10**3,
                    max_wall_clock_seconds=30, _clock=clk)
    assert t.would_exceed() is None
    clk.t += 29.0
    assert t.would_exceed() is None
    clk.t += 2.0  # total 31 ≥ 30
    assert t.would_exceed() == "wall-clock"


def test_unknown_model_keeps_token_cap_binding_no_crash():
    t = CostTracker(max_ai_tokens=100, max_usd=10**6, max_configs=10**3)
    t.record_usage("mystery-model-x", 80, 80)  # unknown → 0 USD, tokens count
    assert t.usd == 0.0
    assert t.ai_tokens == 160
    assert t.would_exceed() == "ai-tokens"  # token cap still binds


def test_snapshot_is_durable_renderable_record():
    t = CostTracker(max_ai_tokens=1000, max_usd=5.0, max_configs=3)
    t.start_config()
    t.record_usage("gpt-5.4-mini", 120, 80)
    snap = t.snapshot()
    assert snap["aiTokens"] == 200
    assert snap["configsRun"] == 1
    assert snap["usd"] == pytest.approx(t.usd)
    assert snap["caps"]["aiTokens"] == 1000
    assert snap["caps"]["configs"] == 3
    # JSON-serialisable primitives only (it is persisted into session.json).
    import json
    json.loads(json.dumps(snap))
