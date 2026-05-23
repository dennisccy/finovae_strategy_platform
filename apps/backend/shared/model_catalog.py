"""Single source of truth for LLM model configuration (Claude + OpenAI).

Every model id, label, default flag, the provider-routing rule, the OpenAI
completion-token caps, and the OpenAI JSON response_format live here — nothing
about models should be hardcoded anywhere else. Backend consumers
(`shared.schemas`, `backend.api`, the strategy generators, `backend.pipeline`)
and the frontend (via ``GET /api/models``) all derive from this module.

This module imports nothing from the rest of the project — keep it dependency-
free so it can be imported from `shared.schemas` without an import cycle.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    """One selectable model. ``provider`` is "openai" or "anthropic"."""

    id: str
    label: str
    provider: str
    default: bool = False


# Order matters: the frontend renders the picker in this order, and the entry
# flagged ``default=True`` is the project-wide default. Exactly one default.
MODELS: list[ModelInfo] = [
    ModelInfo("gpt-5.4-mini", "GPT-5.4 Mini", "openai", default=True),
    ModelInfo("claude-haiku-4-5", "Claude Haiku 4.5", "anthropic"),
    ModelInfo("claude-sonnet-4-5-20250929", "Claude Sonnet 4.5", "anthropic"),
    ModelInfo("claude-sonnet-4-6", "Claude Sonnet 4.6", "anthropic"),
    ModelInfo("claude-opus-4-6", "Claude Opus 4.6", "anthropic"),
]

# Project-wide default model id (the catalog entry flagged default=True).
DEFAULT_MODEL: str = next(m.id for m in MODELS if m.default)

# Named Claude aliases used by the script-generator refinement-downgrade logic
# (Sonnet -> Haiku on refinement). Kept here so model ids live in one place.
SONNET_MODEL: str = "claude-sonnet-4-6"
HAIKU_MODEL: str = "claude-haiku-4-5"
# Back-compat alias (script_generator historically referenced GPT_MINI_MODEL).
GPT_MINI_MODEL: str = DEFAULT_MODEL

# OpenAI hardening config (consolidated; not hardcoded per-file).
# gpt-5.x reasoning tokens count toward max_completion_tokens, so these are 2x
# the corresponding Anthropic max_tokens to leave reasoning headroom — tune here.
OPENAI_MAX_COMPLETION_TOKENS: dict[str, int] = {
    "compiler": 4000,
    "script": 8000,
    "insights": 8000,
}

# JSON-producing OpenAI tasks (compiler, insights) request this. json_object
# guarantees valid JSON; switch to a {"type": "json_schema", ...} object here to
# upgrade to schema-guaranteed Structured Outputs in one place.
OPENAI_JSON_RESPONSE_FORMAT: dict = {"type": "json_object"}


def is_openai_model(model: str) -> bool:
    """True when ``model`` should be routed to the OpenAI client."""
    return model.startswith("gpt-")


def models_payload() -> list[dict]:
    """Serialized model list for the ``GET /api/models`` endpoint / frontend."""
    return [
        {"value": m.id, "label": m.label, "default": m.default} for m in MODELS
    ]


# =============================================================================
# Token usage + token→USD pricing (single source of truth for the cost tracker)
# =============================================================================

@dataclass(frozen=True)
class TokenUsage:
    """Real LLM token usage captured at the SDK response level for ONE call.

    Threaded out of the strategy / insights generators (a side channel, NOT a
    frozen-contract field) into the headless cost tracker
    (``backend.auto_session.BudgetTracker``) so AI-token spend is accounted from
    real usage rather than estimated."""

    input_tokens: int
    output_tokens: int
    model: str

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class TokenRate:
    """Per-model list price, USD per 1,000,000 tokens (input / output)."""

    input_usd_per_1m: float
    output_usd_per_1m: float


# Public list prices (USD per 1,000,000 tokens). THE single source of truth for
# token→USD conversion used by the headless budget tracker — tests assert exact
# costs against these constants, so update pricing here and nowhere else.
MODEL_RATES: dict[str, TokenRate] = {
    "gpt-5.4-mini":               TokenRate(0.15, 0.60),
    "claude-haiku-4-5":           TokenRate(1.00, 5.00),
    "claude-sonnet-4-5-20250929": TokenRate(3.00, 15.00),
    "claude-sonnet-4-6":          TokenRate(3.00, 15.00),
    "claude-opus-4-6":            TokenRate(15.00, 75.00),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Map token counts → USD via the per-model rate table.

    An unknown model id falls back to the project DEFAULT_MODEL rate (the cheap
    default tier) so a typo never silently inflates the budget; the rate table
    IS the source of truth (no estimation elsewhere)."""
    rate = MODEL_RATES.get(model, MODEL_RATES[DEFAULT_MODEL])
    return (input_tokens * rate.input_usd_per_1m
            + output_tokens * rate.output_usd_per_1m) / 1_000_000.0


def cheapest_model() -> str:
    """Return the catalog model id with the lowest blended (input+output) token
    rate — the single source of truth for the "cheap" model tier.

    The headless open-universe SCREEN stage (J-14) routes through this so the
    cheap-first cost-tiering reads the rate table, never a hard-coded id. Today
    this resolves to ``gpt-5.4-mini``. Deterministic: ties are broken by model id."""
    return min(
        MODEL_RATES,
        key=lambda mid: (
            MODEL_RATES[mid].input_usd_per_1m + MODEL_RATES[mid].output_usd_per_1m,
            mid,
        ),
    )
