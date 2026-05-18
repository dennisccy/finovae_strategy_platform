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


## iter-1 — 2026-05-18T03:11:15Z

**Verdict:** CONTINUE
**Lesson:** When an iteration's key new guarantee is "state survives a process restart", the authoritative proof must be a pytest *simulated-restart* test (re-resolve the store fresh + read back), NOT a browser restart test. browser-QA cannot safely kill the shared QA backend + move `.env` unattended (environment-safety policy denies it, no interactive user), so the literal browser restart (UT-05 here) gets SKIPPED and the gate must already rest on functional pytest (TC-08 default-not-`/tmp`-with-env-unset + TC-09 round-trip) plus cross-layer corroboration (browser refresh with empty localStorage, on-disk path, auditor `git rev-parse` of the `Path(__file__).parents[N]` default — never trust a test that derives the expected root via the same `parents[N]` expression as the source). Separately: a structural storage anti-goal ("single Parquet per (symbol,tf), no per-day fan-out, no refetch") is satisfied by code structure regardless of cache directory — the on-disk check here was under `/tmp/market_data` because the dev-managed gitignored runtime `.env` still overrides the new durable default; that is sanctioned (out of scope to commit `.env`), so don't conflate "structural anti-goal met" with "runtime directory is durable".
**Applies to:** any iter whose DoD hinges on restart/persistence durability or on a `Path(__file__).resolve().parents[N]` default; any iter resolving a storage-location anti-goal where runtime `.env` may override the code default.

## iter-2 — 2026-05-18T04:12:47Z

**Verdict:** CONTINUE
**Lesson:** browser-QA saved `UT-J-04-result.png` as a byte-identical duplicate of `UT-J-03-result.png` (both 223797 B, showing the walk-forward panel — not the AI-insights pane). J-04's primary acceptance (>=1 ranked suggestion) was only salvageable here because the insight pills happened to be visible in the *J-05/J-01* screenshots; a strict reading would have had zero dedicated J-04 evidence. The carried J-04 soft gap (insights must be OOS-aware when walk-forward data exists) has never had its own conclusive screenshot in any iteration.
**Applies to:** the next full-depth iteration that must finally assert the J-04 OOS-aware sub-clause — its browser-QA MUST capture a distinct, dedicated screenshot of the *insights pane after a walk-forward run* showing OOS-referencing suggestions, and the evaluator must reject a J-04 screenshot that is a duplicate of the walk-forward (J-03) capture.
