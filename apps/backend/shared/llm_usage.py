"""Real LLM token-usage capture (iter-3 / J-13 support).

The OpenAI / Anthropic SDK response carries a ``.usage`` object the
generators already read for logging and then discard. This helper surfaces
those REAL counts into a caller-supplied sink so the auto-session cost
tracker accumulates *actual* tokens (never an estimate / hardcoded constant).

A "usage sink" is just a ``list`` the caller owns; each captured LLM call
appends one ``{"model", "input_tokens", "output_tokens"}`` dict. Capture is
strictly additive and best-effort: ``usage_sink=None`` (the default
everywhere) is a no-op, and a malformed/absent ``usage`` object never breaks
generation.

This module is dependency-free (no project imports) — it is shared by
``strategy/compiler.py``, ``strategy/script_generator.py`` and
``strategy/insights_generator.py`` without an import cycle and does NOT
touch the frozen ``shared/contracts.py``.
"""

from __future__ import annotations

from typing import Any, Optional


def capture_usage(
    usage_sink: Optional[list],
    model: str,
    response: Any,
    *,
    openai: bool,
) -> None:
    """Append this LLM call's REAL token usage to ``usage_sink``.

    OpenAI exposes ``usage.prompt_tokens`` / ``usage.completion_tokens``;
    Anthropic exposes ``usage.input_tokens`` / ``usage.output_tokens``. Both
    are normalised to ``input_tokens`` / ``output_tokens``.

    No-op when ``usage_sink`` is ``None`` or the response has no usable
    ``usage`` (best-effort: capturing tokens must never fail a generation).
    """
    if usage_sink is None:
        return
    u = getattr(response, "usage", None)
    if not u:
        return
    try:
        if openai:
            it = getattr(u, "prompt_tokens", 0)
            ot = getattr(u, "completion_tokens", 0)
        else:
            it = getattr(u, "input_tokens", 0)
            ot = getattr(u, "output_tokens", 0)
        usage_sink.append({
            "model": model,
            "input_tokens": int(it or 0),
            "output_tokens": int(ot or 0),
        })
    except Exception:  # noqa: BLE001 - usage capture is strictly best-effort
        pass
