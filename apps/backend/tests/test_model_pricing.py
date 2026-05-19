"""Static per-model USD price table (iter-3 / J-13).

The price table is a hard-coded constant keyed by model id — NOT a paid
pricing API. USD spend is derived from real captured token counts × this
table. An unknown model must not crash and must contribute 0 USD so the
AI-token cap stays the binding hard ceiling.
"""

from __future__ import annotations

import pytest

from shared.model_catalog import (
    MODEL_PRICING,
    MODELS,
    cheapest_model,
    model_token_prices,
    usd_cost,
)


def test_every_catalog_model_has_a_price_entry():
    """The price table must stay in sync with the model catalog (single
    source of truth) — a selectable model with no price would silently
    under-count USD spend."""
    catalog_ids = {m.id for m in MODELS}
    missing = catalog_ids - set(MODEL_PRICING)
    assert not missing, f"models missing from MODEL_PRICING: {sorted(missing)}"


def test_known_model_prices_are_positive_input_lt_output():
    for model_id, (p_in, p_out) in MODEL_PRICING.items():
        assert p_in > 0.0, f"{model_id} input price must be > 0"
        assert p_out > 0.0, f"{model_id} output price must be > 0"
        assert p_out >= p_in, f"{model_id} output should not be cheaper than input"


def test_usd_cost_is_tokens_times_table_exactly():
    p_in, p_out = model_token_prices("gpt-5.4-mini")
    # Exact arithmetic: cost == in*price_in + out*price_out (no rounding here).
    assert usd_cost("gpt-5.4-mini", 1000, 500) == pytest.approx(
        1000 * p_in + 500 * p_out
    )


def test_unknown_model_costs_zero_and_does_not_crash():
    assert model_token_prices("totally-made-up-model") == (0.0, 0.0)
    # Unknown model → 0 USD (the token cap remains the binding ceiling).
    assert usd_cost("totally-made-up-model", 999999, 999999) == 0.0


def test_usd_cost_clamps_negative_or_none_token_counts():
    assert usd_cost("gpt-5.4-mini", -5, -10) == 0.0
    assert usd_cost("gpt-5.4-mini", None, None) == 0.0  # type: ignore[arg-type]


def test_cheapest_model_is_resolved_from_the_price_table_not_a_literal():
    """J-14 SCREEN routing: the cheapest model MUST be derived from
    MODEL_PRICING (lowest combined per-token cost), not a hardcoded id —
    so it tracks the table if pricing changes / a cheaper model is added."""
    expected = min(
        MODEL_PRICING,
        key=lambda m: (MODEL_PRICING[m][0] + MODEL_PRICING[m][1], m),
    )
    chosen = cheapest_model()
    assert chosen == expected
    # It is a real catalog model and is genuinely the cheapest entry.
    assert chosen in {m.id for m in MODELS}
    cheapest_cost = sum(MODEL_PRICING[chosen])
    for model_id, (p_in, p_out) in MODEL_PRICING.items():
        assert cheapest_cost <= p_in + p_out, (
            f"{model_id} is cheaper than the resolved cheapest {chosen}"
        )
