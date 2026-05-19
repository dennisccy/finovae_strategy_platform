"""Immutable hard cost tracker for the headless auto-session (J-13).

The moment open-universe exploration lands (J-12), the goal's strongest
budget anti-goal activates: an open universe bounded only by
``max_iterations`` / wall-clock would be an unbounded-cost exposure. This
tracker is that hard ceiling. It enforces — independently and
simultaneously — a cap on **AI tokens**, **USD**, **max-configs**, and
**wall-clock**:

  * accumulated spend is monotonic / append-only — it can only ever
    increase (a negative/None usage delta is ignored, never a refund);
  * the caps are FIXED at construction in a frozen dataclass — there is no
    public mutator, so a run can never take "one more round" by widening
    its own budget mid-flight;
  * an absent / zero / negative cap falls back to a SAFE FINITE default —
    the loop is hard-bounded even when no budget is supplied, never
    unbounded;
  * USD is derived from the REAL captured token counts × the static
    per-model price table in :mod:`shared.model_catalog` (an unknown model
    contributes 0 USD but its tokens still count, so the token cap stays
    binding and nothing crashes).

The controller checks :meth:`would_exceed` *before* starting each
config/round ("no one more config/round past the cap"); a single in-flight
LLM call may marginally exceed (the goal's within-one-call tolerance) but no
new config/round begins once any cap is reached.

This module is dependency-light (only the price table) so it is trivially
unit-testable and reusable by the auto-session controller without import
cycles. It does NOT touch the frozen ``shared/contracts.py``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

from shared.model_catalog import usd_cost

# --- Safe finite defaults + absolute hard ceilings (mirrors the
# ``DEFAULT_MAX_ITERATIONS`` / ``HARD_MAX_ITERATIONS`` pattern in
# auto_session.py). Defaults are large enough not to interfere with a normal
# pinned run but FINITE — the run is always hard-bounded, never unbounded. ---
DEFAULT_MAX_AI_TOKENS = 5_000_000
HARD_MAX_AI_TOKENS = 50_000_000
DEFAULT_MAX_USD = 25.0
HARD_MAX_USD = 250.0
DEFAULT_MAX_CONFIGS = 3
HARD_MAX_CONFIGS = 64
HARD_MAX_WALL_CLOCK_SECONDS = 24 * 3600.0


@dataclass(frozen=True)
class CostCaps:
    """The hard caps, fixed at tracker construction. Frozen: a mid-run
    attempt to widen the budget raises ``FrozenInstanceError`` rather than
    silently succeeding."""

    max_ai_tokens: int
    max_usd: float
    max_configs: int
    max_wall_clock_seconds: Optional[float]


def _resolve_caps(
    *,
    max_ai_tokens: Optional[int],
    max_usd: Optional[float],
    max_configs: Optional[int],
    max_wall_clock_seconds: Optional[float],
    default_max_configs: int,
    hard_max_configs: int,
) -> CostCaps:
    """Clamp every cap so the run can never be unbounded.

    Absent / <= 0 → the safe finite default; any supplied value is clamped
    to the absolute hard ceiling. ``max_wall_clock_seconds`` absent / <= 0
    means *no* wall cap (the token/usd/config caps still hard-bound the run)
    — this preserves the pre-iter-3 behaviour where wall-clock was optional.
    """
    if max_ai_tokens is None or max_ai_tokens <= 0:
        tokens = DEFAULT_MAX_AI_TOKENS
    else:
        tokens = min(int(max_ai_tokens), HARD_MAX_AI_TOKENS)

    if max_usd is None or max_usd <= 0:
        usd = DEFAULT_MAX_USD
    else:
        usd = min(float(max_usd), HARD_MAX_USD)

    if max_configs is None or max_configs <= 0:
        configs = default_max_configs
    else:
        configs = min(int(max_configs), hard_max_configs)

    if max_wall_clock_seconds is None or max_wall_clock_seconds <= 0:
        wall: Optional[float] = None
    else:
        wall = min(float(max_wall_clock_seconds), HARD_MAX_WALL_CLOCK_SECONDS)

    return CostCaps(tokens, usd, configs, wall)


class CostTracker:
    """Monotonic spend accumulator with immutable, construction-fixed caps.

    ``_clock`` is injectable so the wall-clock cap is deterministically
    unit-testable (no flaky sleeps).
    """

    def __init__(
        self,
        *,
        max_ai_tokens: Optional[int] = None,
        max_usd: Optional[float] = None,
        max_configs: Optional[int] = None,
        max_wall_clock_seconds: Optional[float] = None,
        default_max_configs: int = DEFAULT_MAX_CONFIGS,
        hard_max_configs: int = HARD_MAX_CONFIGS,
        _clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._caps = _resolve_caps(
            max_ai_tokens=max_ai_tokens,
            max_usd=max_usd,
            max_configs=max_configs,
            max_wall_clock_seconds=max_wall_clock_seconds,
            default_max_configs=default_max_configs,
            hard_max_configs=hard_max_configs,
        )
        self._clock = _clock
        self._start = _clock()
        self._tokens = 0
        self._usd = 0.0
        self._configs = 0

    # --- read-only spend / caps -------------------------------------------
    @property
    def caps(self) -> CostCaps:
        return self._caps

    @property
    def ai_tokens(self) -> int:
        return self._tokens

    @property
    def usd(self) -> float:
        return self._usd

    @property
    def configs_run(self) -> int:
        return self._configs

    def elapsed_seconds(self) -> float:
        return max(0.0, self._clock() - self._start)

    # --- monotonic accumulation -------------------------------------------
    def record_usage(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> None:
        """Accumulate one REAL LLM call's token usage (append-only).

        A negative / ``None`` delta is ignored — spend never decreases (no
        "refund" can be used to cheat a hard cap).
        """
        it = max(0, int(input_tokens or 0))
        ot = max(0, int(output_tokens or 0))
        if it == 0 and ot == 0:
            return
        self._tokens += it + ot
        self._usd += usd_cost(model, it, ot)

    def start_config(self) -> None:
        """Count one explored config/round. Monotonic; call it once a
        per-round budget check has already passed."""
        self._configs += 1

    # --- hard ceiling -----------------------------------------------------
    def would_exceed(self) -> Optional[str]:
        """Name of the first cap that is reached, else ``None``.

        Checked BEFORE starting each config/round so no new config/round
        begins once any cap is hit ("no one more round past the cap"). Each
        cap is evaluated independently.
        """
        if self._tokens >= self._caps.max_ai_tokens:
            return "ai-tokens"
        if self._usd >= self._caps.max_usd:
            return "usd"
        if self._configs >= self._caps.max_configs:
            return "max-configs"
        wall = self._caps.max_wall_clock_seconds
        if wall is not None and self.elapsed_seconds() >= wall:
            return "wall-clock"
        return None

    # --- durable, UI-renderable record ------------------------------------
    def snapshot(self) -> dict:
        """JSON-safe spend record persisted into the durable ``autoRun``
        block and rendered in the existing ``AutoRunBar``."""
        return {
            "aiTokens": self._tokens,
            "usd": round(self._usd, 6),
            "configsRun": self._configs,
            "wallClockSeconds": round(self.elapsed_seconds(), 3),
            "caps": {
                "aiTokens": self._caps.max_ai_tokens,
                "usd": self._caps.max_usd,
                "configs": self._caps.max_configs,
                "wallClockSeconds": self._caps.max_wall_clock_seconds,
            },
        }
