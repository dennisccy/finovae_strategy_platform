"""Robust objective for the headless auto-session (Key Capability #11).

A single scalar that selects the *best* iteration by a walk-forward,
WFE-gated, min-trades-floored, drawdown- and over-leverage-penalised
measure — explicitly NOT by raw return. The deep overfit-gating stress
test is a later journey (J-16); the selector itself must exist now so
J-09's "best marked" / "criteria-met" semantics are real.

This module is intentionally dependency-free (pure functions + a frozen
input dataclass) so it is trivially unit-testable and can be reused by the
auto-session controller without import cycles. It does NOT touch the frozen
``shared/contracts.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

# Default gates. Lenient enough that a healthy strategy on a short tiny-budget
# window can clear them, strict enough that a non-walk-forward-validated or
# under-traded candidate is held back.
DEFAULT_MIN_WFE = 0.3
DEFAULT_MIN_TRADES = 5

# Subtracted from the score when a hard gate fails. Large enough that any
# gate-passing candidate always ranks above any gate-failing one, so a
# higher-raw-return-but-WFE-failing candidate can never be selected as best.
_GATE_FAIL_PENALTY = 1000.0


@dataclass(frozen=True)
class RobustInputs:
    """The metrics the robust objective consumes for one iteration.

    ``wfe`` / ``oos_*`` / ``num_windows`` come from walk-forward validation
    and are ``None`` / 0 when WF did not run or produced no windows.
    """

    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    num_trades: int
    leverage: float = 1.0
    wfe: Optional[float] = None
    oos_return: Optional[float] = None
    oos_sharpe: Optional[float] = None
    num_windows: int = 0


def _finite(x: float) -> float:
    """Collapse non-finite scores to a very-low finite value (never inf/nan)."""
    return x if math.isfinite(x) else -_GATE_FAIL_PENALTY * 10.0


def has_walk_forward(inp: RobustInputs) -> bool:
    """True when walk-forward produced at least one window with a WFE."""
    return inp.num_windows > 0 and inp.wfe is not None


def robust_score(
    inp: RobustInputs,
    *,
    min_wfe: float = DEFAULT_MIN_WFE,
    min_trades: int = DEFAULT_MIN_TRADES,
) -> float:
    """Compute the single robust scalar for one iteration.

    The base reward is the *out-of-sample* risk-adjusted return when
    walk-forward data exists; without WF the in-sample Sharpe is heavily
    discounted (an un-validated strategy is not trustworthy). Drawdown and
    over-leverage are penalised. Failing any hard gate (WF present, WFE >=
    threshold, min-trades floor) applies a large fixed penalty so a
    gate-failing candidate can never outrank a gate-passing one regardless
    of raw return.
    """
    wf = has_walk_forward(inp)
    if wf:
        base = inp.oos_sharpe if inp.oos_sharpe is not None else inp.sharpe_ratio
    else:
        base = inp.sharpe_ratio * 0.25

    drawdown = max(0.0, min(1.0, inp.max_drawdown))
    score = base - 2.0 * drawdown

    if inp.leverage and inp.leverage > 1.0:
        score -= 0.5 * (inp.leverage - 1.0)

    gate_pass = (
        wf
        and inp.wfe is not None
        and inp.wfe >= min_wfe
        and inp.num_trades >= min_trades
    )
    if not gate_pass:
        score -= _GATE_FAIL_PENALTY

    return _finite(score)


def targets_met(inp: RobustInputs, targets: Optional[dict]) -> bool:
    """True only when EVERY supplied robust target is satisfied.

    An absent/empty ``targets`` returns False: with no targets the run can
    only stop on the hard budget (``budget-exhausted``), never
    ``criteria-met``. ``min_wfe`` additionally requires real walk-forward
    data (no WF ⇒ the WFE target cannot be met).
    """
    if not targets:
        return False

    min_wfe = targets.get("min_wfe")
    if min_wfe is not None:
        if not has_walk_forward(inp) or inp.wfe is None or inp.wfe < min_wfe:
            return False

    min_trades = targets.get("min_trades")
    if min_trades is not None and inp.num_trades < min_trades:
        return False

    min_sharpe = targets.get("min_sharpe")
    if min_sharpe is not None and inp.sharpe_ratio < min_sharpe:
        return False

    min_return = targets.get("min_return")
    if min_return is not None and inp.total_return < min_return:
        return False

    return True


def select_best(
    candidates: list[tuple[str, RobustInputs]],
    *,
    targets: Optional[dict] = None,
    require_targets: bool = False,
    min_wfe: float = DEFAULT_MIN_WFE,
    min_trades: int = DEFAULT_MIN_TRADES,
) -> Optional[str]:
    """Pick the best iteration id by robust score.

    When ``require_targets`` is True (the run stopped ``criteria-met``),
    only iterations that satisfy every supplied target are eligible — this
    guarantees J-09's invariant that a ``criteria-met`` best actually meets
    all targets. If that filter leaves nothing eligible, fall back to the
    global best so a best is always marked.
    """
    if not candidates:
        return None

    pool = candidates
    if require_targets and targets:
        eligible = [c for c in candidates if targets_met(c[1], targets)]
        if eligible:
            pool = eligible

    best_id: Optional[str] = None
    best_score = -math.inf
    for cid, inp in pool:
        score = robust_score(inp, min_wfe=min_wfe, min_trades=min_trades)
        if score > best_score:
            best_score = score
            best_id = cid
    return best_id
