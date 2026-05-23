# Goal iter-1 — Implementation Summary

**Phase:** goal-financial_free-iter-1
**Date:** 2026-05-23
**Written by:** developer

---

## Features Implemented

- **Start an automated strategy session with one API call**: A new endpoint
  `POST /api/auto-sessions` accepts a plain-English strategy plus a pinned
  config (symbol, timeframe, date range, capital, optional targets) and a
  required budget, then starts a fully server-side strategy search. No browser,
  no clicking, no manual backtest — the platform "runs itself" from a single
  call. The created session shows up immediately in the existing session list
  and is browsed exactly like a manual one.
- **Runs to a clear finish and marks the best strategy**: The automated session
  seeds a baseline strategy, then tries AI-suggested improvements round by round
  until it either (a) meets the success targets you supplied (`criteria-met`),
  or (b) hits its hard budget (`budget-exhausted`). It always marks a single
  "best" iteration, chosen by a skeptical, walk-forward-validated objective — a
  flashier-looking result that fails out-of-sample validation is not allowed to
  win.
- **Hard budget that cannot be overrun**: Every run honors a hard cap on the
  number of improvement rounds (and, optionally, a wall-clock limit). The loop
  checks the budget before each round and stops cleanly — it never sneaks in
  "one more round" past the cap.
- **Live, durable run status**: Each automated session carries a status block
  (`autoRun`) showing its run state, stop reason, best-iteration marker, and
  budget counters. It is saved to the durable file store and is visible on the
  existing session record (`GET /api/sessions/{id}`), so it survives a server
  restart or a browser reload.
- **Stop control (plumbing)**: `POST /api/auto-sessions/{id}/stop` requests a
  graceful stop; the run finishes its current step and transitions to `stopped`,
  keeping the best-so-far. (The user-facing stop button is a later iteration —
  this iteration ships the underlying capability.)
- **Self-healing after a crash**: If the server is restarted while a run is in
  flight, that run is automatically marked `interrupted` on next startup instead
  of being stuck "running" forever.

---

## Changed Behavior

- **`GET /api/sessions/{id}` now includes an `autoRun` field**: For automated
  sessions it carries the status block described above; for ordinary (manual)
  sessions it is simply `null`. Nothing else about that endpoint changed — it
  stays lightweight and still loads heavy run detail only on demand.
- **No change to any manual workflow.** Running a backtest, browsing history,
  walk-forward, AI insights, reference data, and warm-cache re-runs all behave
  exactly as before. The automated loop reuses the very same backtest engine,
  sandbox, and file store, so a headless run produces records indistinguishable
  from a manual one.

---

## Backend-Only Items

This entire iteration is backend-only by design (the plan's "Frontend Present:
no"). The new capability is reachable via the API and is **visible** in the
existing UI because the created session appears in the normal session list and
its iterations render through the existing session view. The pieces with no
*new* dedicated UI control yet:

- `POST /api/auto-sessions` (start) — no dedicated "Start automated session"
  button in the UI yet; the created session is visible in the existing session
  picker. (UI start/track controls are the next iteration: J-08/J-10/J-11.)
- `POST /api/auto-sessions/{id}/stop` (stop) — no UI stop button yet (J-11).
- `autoRun` status block — surfaced in the API response and persisted; the live
  in-UI status strip / auto-refresh is the next iteration (J-08).

---

## Incomplete Items

All items in this iteration's spec scope are complete. Explicitly **out of
scope** here (and intentionally not done — they belong to later iterations):

- **Open-universe runs** (start a search with no symbol/timeframe): deliberately
  **rejected with a clear 400** this iteration — it is the Layer-2 optimizer
  (J-12).
- **Hard token/USD budget caps**: only round-count and wall-clock are hard caps
  here; token/USD are recorded as best-effort counters (J-13).
- **In-UI live tracking, the in-browser→backend rewire, and the UI stop button**
  (J-08/J-10/J-11): next iteration.
- **Staged screening, history warm-start, leaderboard** (J-14/J-15/J-16):
  Layer-2.

---

## Config and Environment Changes

- **No new environment variables, no new dependencies, no new infrastructure.**
  The automated session reuses the existing file store
  (`BACKTEST_STORE_DIR`) and the existing one-backtest-per-worker concurrency
  limit. No database, queue, or broker was added.
- `OPENAI_API_KEY` is used (as today) for real strategy generation/insights when
  a run executes; the backend still boots without it.

---

## Known Limitations

- **Token/USD spend is reported best-effort, not hard-capped this iteration.** A
  run stops on round-count or wall-clock, not on token/dollar spend. (Hard
  token/cost enforcement is J-13.) All automated runs should still use tiny
  budgets per project policy.
- **No new UI controls yet.** You start and stop automated sessions via the API;
  the in-UI buttons and live auto-refresh arrive next iteration. The created
  session is, however, fully visible and browsable in the existing UI now.
- **The legacy in-browser "Auto Run" loop still exists** and remains the manual
  Auto Run path for now. It is a known, scheduled duplicate that the next
  iteration removes when it rewires Auto Run to this backend loop; the backend's
  walk-forward-gated scorer is the canonical "best" definition going forward.
- **Walk-forward on a very short date range may produce zero windows**, in which
  case a candidate is treated as un-validated (it cannot be marked "best" purely
  on raw return). Use a date range long enough for at least one in-sample +
  out-of-sample window when you want the validation gate to bite.
