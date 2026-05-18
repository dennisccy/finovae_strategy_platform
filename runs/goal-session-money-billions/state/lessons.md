# Goal Session money-billions — Lessons Learned

Append-only ledger of takeaways from prior iterations. The goal-evaluator
appends one entry per iteration; the goal-decomposer reads this file before
planning each iteration to avoid repeating known pitfalls.

Each entry should be 1-3 sentences capturing a non-obvious lesson — surprising
failures, regression triggers, or decisions that worked well. Avoid
restating the verdict (the evaluator-log.md already does that).

## iter-0 — 2026-05-18T00:35:26Z

**Verdict:** CONTINUE
**Lesson:** J-05's failure is "the UI never calls healthy endpoints," not "broken endpoints" — `/api/symbols` & `/api/timeframes` return correct data but `BacktestConfigBar.tsx` uses a hardcoded timeframe literal (line 61) and a free-text symbol input (lines 43-54). A `Mode:next` iteration must NOT touch the backend endpoints; the fix is purely frontend wiring. Separately, J-06 passes FUNCTIONALLY (warm re-run works) while the single-Parquet anti-goal is still violated (per-day CSV under `/tmp`) — a green J-06 must never be read as "Parquet/durable-store anti-goal satisfied"; they are independent.
**Applies to:** any iter scoping J-05 (frontend-only — do not modify `/api/symbols`/`/api/timeframes`); any iter touching `data/loader.py` / `session_store.py` storage (the per-day-CSV + `/tmp`-default divergences are PRE-EXISTING baseline state, not a regression introduced by the touching iter — and verify J-01/J-06 still pass after the Parquet migration).

