#!/usr/bin/env python3
"""Seed a REAL open-universe auto-session into the live file store so the actual
AutoSessionLeaderboard component can be rendered to pixels (J-16 capture).

This is NOT a parallel store or a schema fork — it drives the real
``AutoSessionController`` (with the hermetic ``FakePipeline``, no live LLM/Binance)
against the SAME durable file store the running backend serves. The persisted
``session.json``/iteration nodes are byte-identical in shape to a live run, so the
UI renders them through the normal ``GET /api/sessions/{id}`` path.

The sequence is the binding J-16 fixture
(``test_overfit_gating_higher_return_wfe_fail_not_best``):
  * A — BTC/USDT 1h: raw return 0.9, WFE 0.10  -> eligible:false, "WFE..." reason (NOT best)
  * B — ETH/USDT 1h: raw return 0.3, WFE 0.60  -> eligible:true, the marked best
  * C — BTC/USDT 4h: screen-only               -> "screened — not walk-forward validated"

So the rendered leaderboard shows all four DoD pixel elements: >=2 ranked rows,
the highlighted BEST row (== bestIterationId), color-graded WFE chips
(red 0.10 / emerald 0.60 / "—" for screen), and a non-best candidate's gating
reason (the WFE-failing rejection).

Run from apps/backend with the backend venv:
    .venv/bin/python ../../reports/qa/goal-financial_free-iter-8-evidence/seed_leaderboard_session.py
"""
import asyncio
import time

import backend.session_store as ss
from backend.auto_session import AutoSessionController, BudgetTracker
from tests.auto_session_helpers import FakePipeline, FakeSpec, build_config

SID = "j16-leaderboard-proof"


async def main() -> None:
    ss.initialize()  # real BASE_DIR (no monkeypatch) — the store the live backend serves
    # Clean any prior copy so re-runs are deterministic.
    try:
        ss.delete_session(SID)
    except Exception:
        pass

    cfg = build_config(symbol=None, timeframe=None, natural_language="", promote_k=2)
    seq = [
        FakeSpec(total_return=0.9, sharpe=1.0, num_trades=10, max_drawdown=0.05),              # A top screen
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05),              # B 2nd screen
        FakeSpec(total_return=0.1, sharpe=1.0, num_trades=10, max_drawdown=0.05),              # C screen-only
        FakeSpec(total_return=0.9, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.10),    # A promote -> WFE fail
        FakeSpec(total_return=0.3, sharpe=1.0, num_trades=10, max_drawdown=0.05, wfe=0.60),    # B promote -> best
    ]
    fake = FakePipeline(sequence=seq)
    ctrl = AutoSessionController(
        SID, cfg, BudgetTracker(max_iterations=9, max_configs=3), fake, open_universe=True
    )
    auto_run = await ctrl.run()

    # Make this the most-recently-accessed session so the UI auto-opens it on load
    # (App.tsx selects sorted-by-lastAccessedAt[0]). Merges — preserves autoRun.
    ss.write_session_meta(
        SID,
        {"name": "J-16 Overfit-Gating Leaderboard (proof)", "lastAccessedAt": int(time.time() * 1000)},
    )

    print("session:", SID)
    print("status:", auto_run["status"], "best:", auto_run["bestIterationId"])
    for e in auto_run["leaderboard"]:
        print(f"  {e['stage']:8s} score={e['robustScore']} eligible={e['eligible']} | {e['gatingReason']}")


if __name__ == "__main__":
    asyncio.run(main())
