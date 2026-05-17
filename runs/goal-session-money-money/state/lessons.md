# Goal Session money-money — Lessons Learned

Append-only ledger of takeaways from prior iterations. The goal-evaluator
appends one entry per iteration; the goal-decomposer reads this file before
planning each iteration to avoid repeating known pitfalls.

Each entry should be 1-3 sentences capturing a non-obvious lesson — surprising
failures, regression triggers, or decisions that worked well. Avoid
restating the verdict (the evaluator-log.md already does that).

## iter-0 — 2026-05-17T23:10:05Z

**Verdict:** CONTINUE
**Lesson:** The `BACKTEST_STORE_DIR`/`DIRECTIONS_CACHE_DIR` durability anti-goal is *masked at runtime* by an `apps/backend/.env` override (boot log shows `.data/backtests`) while the code defaults (`session_store.py:26`, `directions_cache.py:23`) are still volatile `/tmp` — a fix that only edits `.env` will look green here but leave the anti-goal intact in any env without that override; the *code default* must change. Separately, browser-qa emitted one byte-identical capture for two journeys (`UT-J-03`==`UT-J-04`, md5 8eb37896…) — always md5-check evidence before trusting per-journey screenshots.
**Applies to:** any iter remediating `BACKTEST_STORE_DIR`/`DIRECTIONS_CACHE_DIR` defaults or the OHLCV cache layout, and any evaluation relying on per-journey screenshot evidence (verify distinct captures).
