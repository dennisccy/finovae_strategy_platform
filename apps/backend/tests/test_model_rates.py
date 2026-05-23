"""Token→USD pricing tests for shared/model_catalog.py (J-13 accounting).

The rate table IS the single source of truth for token→USD conversion used by
the headless budget tracker, so these assert EXACT costs against the constants.
"""

import pytest

from shared.model_catalog import (
    DEFAULT_MODEL,
    MODEL_RATES,
    TokenUsage,
    cheapest_model,
    cost_usd,
)


def test_cost_usd_exact_for_default_model():
    # gpt-5.4-mini = $0.15 / 1M input, $0.60 / 1M output.
    # 1000 in + 1000 out = (1000*0.15 + 1000*0.60) / 1e6 = 0.00075 USD.
    assert cost_usd("gpt-5.4-mini", 1000, 1000) == pytest.approx(0.00075)


def test_cost_usd_zero_tokens_is_zero():
    assert cost_usd("gpt-5.4-mini", 0, 0) == 0.0


def test_cost_usd_premium_model_costs_more_than_default():
    assert cost_usd("claude-opus-4-6", 1000, 1000) > cost_usd("gpt-5.4-mini", 1000, 1000)


def test_cost_usd_unknown_model_falls_back_to_default_rate():
    # An unknown id must price identically to the project default model.
    assert cost_usd("totally-made-up-model", 1234, 567) == pytest.approx(
        cost_usd(DEFAULT_MODEL, 1234, 567)
    )


def test_every_catalog_model_has_a_rate():
    from shared.model_catalog import MODELS
    for m in MODELS:
        assert m.id in MODEL_RATES, f"missing rate for {m.id}"


def test_token_usage_total():
    u = TokenUsage(input_tokens=600, output_tokens=400, model="gpt-5.4-mini")
    assert u.total_tokens == 1000


# =============================================================================
# cheapest_model — single source of truth for the SCREEN-stage model tier (J-14)
# =============================================================================

def test_cheapest_model_is_min_rate_catalog_model():
    # The SCREEN stage of the open-universe search routes through this, so it
    # MUST be the lowest blended (input+output) rate in the table — gpt-5.4-mini.
    assert cheapest_model() == "gpt-5.4-mini"


def test_cheapest_model_has_lowest_blended_rate_of_all():
    cheapest = cheapest_model()
    blended = {mid: r.input_usd_per_1m + r.output_usd_per_1m for mid, r in MODEL_RATES.items()}
    assert blended[cheapest] == min(blended.values())
    # It is strictly cheaper than every other catalog model (no tie at the floor here).
    assert all(blended[cheapest] < v for mid, v in blended.items() if mid != cheapest)


def test_cheapest_model_is_a_real_catalog_entry():
    from shared.model_catalog import MODELS
    assert cheapest_model() in {m.id for m in MODELS}
