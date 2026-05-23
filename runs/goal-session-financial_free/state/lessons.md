# Goal Session financial_free — Lessons Learned

Append-only ledger of takeaways from prior iterations. The goal-evaluator
appends one entry per iteration; the goal-decomposer reads this file before
planning each iteration to avoid repeating known pitfalls.

Each entry should be 1-3 sentences capturing a non-obvious lesson — surprising
failures, regression triggers, or decisions that worked well. Avoid
restating the verdict (the evaluator-log.md already does that).

## iter-0 — 2026-05-23T01:01:12Z

**Verdict:** CONTINUE
**Lesson:** A functionally-green J-02 (run-history browse) does NOT prove the eager-load
anti-goal is satisfied: the `GET /api/sessions` list path and the per-iteration detail
fetch are correctly lazy, yet the single-session OPEN path `GET /api/sessions/{id}` still
ships ~245KB and embeds `equity_curve` in its summary nodes. Heavy detail being lazy does
not mean the open payload is lean — these are separate code paths that must be checked
independently.
**Applies to:** any iter touching `apps/backend/backend/session_routes.py` /
`session_store.py` or the session-open contract, and the coherence-auditor when a diff
reaches the sessions surface — deliver a definitive verdict on whether the open-path
`equity_curve` embed violates the "no eager full-payload parse" anti-goal.

## iter-1 — 2026-05-23T08:33:05Z

**Verdict:** CONTINUE
**Lesson:** The obvious fix for the "store writes block the event loop" note (wrap the controller's `session_store` calls in `await asyncio.to_thread`) must NOT be applied alone — it converts the controller's currently event-loop-atomic read-modify-write of the persisted `autoRun.stopRequested` flag into an interleaved RMW against the lock-free `/stop` writer, *widening* a TOCTOU race that drops a stop request. The non-blocking fix (B1) and the stop-flag integrity fix (B2) are one design problem (single-writer / async lock), to be solved together when J-10/J-11 actually claim the stop journey. Also: byte-shape identity between the manual SSE path and the headless loop was guaranteed by *extracting* serialization into one shared `result_serialization.py` (not by a parallel reimplementation) — keep this single source when the frontend rewire lands; do not re-fork it.
**Applies to:** any iter touching `apps/backend/backend/auto_session.py` autoRun persistence, the `/stop` endpoint, or wiring `to_thread` around the controller's store I/O (J-10/J-11/iter-2); and any iter that changes backtest result/rating/walk-forward serialization (keep `result_serialization.py` as the one source).
