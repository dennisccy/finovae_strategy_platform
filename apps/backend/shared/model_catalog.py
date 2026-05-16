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
