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

## iter-2 — 2026-05-23T10:11:19Z

**Verdict:** CONTINUE
**Lesson:** UI-load-bearing journeys keep failing to capture browser pixels for a *different* reason each iteration — iter-0 was the hidden-tab render throttle (blank pixels), iter-2 the Vite dev server returned HTTP 000 (up at QA start, **down by the browser-qa window**). Both fell back to backend-endpoint + static-code verification, which is spec-sanctioned and sufficient for a CONTINUE, but it means J-08's "live strip updates / cards stream without reload" and J-10's reload-survival have *never* been confirmed at the pixel layer — the debt is now compounding into Layer-2 (also UI-bearing). Don't just launch the frontend before browser-qa; **health-check it is still serving for the whole window** (and re-probe mid-run), or the pixel debt will silently roll forward again.
**Applies to:** any iteration whose Definition-of-Done lists browser journeys by ID as load-bearing (Layer-2 J-16 leaderboard UI; any future UI-surfacing iter) — verify the frontend stays up across the entire browser-qa window, and treat an accumulated unverified-pixel journey as a debt to clear, not re-defer.
