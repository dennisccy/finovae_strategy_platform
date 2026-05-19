# goal-auto-money-printer-iter-1 Functional Test Plan

**Phase:** goal-auto-money-printer-iter-1
**Date:** 2026-05-19
**Frontend Present:** yes

## Phase Goal

One `POST /api/auto-sessions` call with a pinned config + tiny budget runs the
generate→backtest→insights→iterate loop entirely server-side; the session appears
immediately in the existing UI session list, updates live with no manual reload, and
reaches a terminal state with a visible stop reason and a best iteration marked by a
robust (WFE-gated, drawdown-penalized) objective. Plus the lesson-mandated J-02 fix:
opening a prior run re-binds the RIGHT analysis panel (trades + equity + WF).

**Tiny-budget config used by all live/browser cases** (per goal.md): `natural_language`
= `"Buy when RSI crosses below 30, sell when it crosses above 70"`, `symbol` =
`"BTCUSDT"`, `timeframe` = `"1h"`, `start_date` = `"2024-01-01"`, `end_date` =
`"2024-01-15"`, `initial_capital` = `10000`, `model` = `"gpt-5.4-mini"` (cheapest
default), lenient `targets` (e.g. `{"min_wfe":0.0,"min_trades":0,"min_return":-1.0}`),
`budget` = `{"max_iterations":2}`. Backend `http://localhost:8000`, UI
`http://localhost:3000`.

## Test Cases

### TC-01 — Start headless session via API (J-07 happy path)

**Type:** api
**Preconditions:** backend running on :8000; `OPENAI_API_KEY` present.

**Steps:**
1. `curl -sS -w "\n%{http_code}" -X POST http://localhost:8000/api/auto-sessions -H 'Content-Type: application/json' -d '{"natural_language":"Buy when RSI crosses below 30, sell when it crosses above 70","symbol":"BTCUSDT","timeframe":"1h","start_date":"2024-01-01","end_date":"2024-01-15","initial_capital":10000,"model":"gpt-5.4-mini","targets":{"min_wfe":0.0,"min_trades":0,"min_return":-1.0},"budget":{"max_iterations":2}}'`
2. Capture `sessionId` from the JSON body.

**Expected outcome:** HTTP 200; body is JSON containing a non-empty `sessionId` and `status` ∈ {`running`,`queued`}.
**Pass criteria:** status code == 200 AND `sessionId` is a non-empty string AND `status` is exactly `running` or `queued`.

---

### TC-02 — Headless session appears immediately in the session list (J-07)

**Type:** api
**Preconditions:** TC-01 ran; its `sessionId` captured.

**Steps:**
1. Within ~2s of TC-01 (no UI interaction), run `curl -sS http://localhost:8000/api/sessions`.

**Expected outcome:** the response lists the session created in TC-01.
**Pass criteria:** the `sessionId` from TC-01 is present in the `GET /api/sessions` response payload.

---

### TC-03 — `GET /api/sessions/{id}` returns the autoRun block without eager iteration parsing (anti-goal: lazy-load)

**Type:** api
**Preconditions:** TC-01 `sessionId` available.

**Steps:**
1. `curl -sS http://localhost:8000/api/sessions/<sessionId>`.
2. Inspect the JSON for an `autoRun` object and confirm no full per-iteration `result`/`rating` payloads are inlined.

**Expected outcome:** response includes an `autoRun` status object (status/stopReason/currentIteration/maxIterations/bestIterationId/startedAt/updatedAt) and does NOT embed per-iteration `result.json`/`rating.json` arrays.
**Pass criteria:** `autoRun` present with those keys AND response contains no inlined per-iteration result/rating bodies (iteration detail still via the existing per-iteration endpoint).

---

### TC-04 — Missing required pinned field rejected cleanly (error case)

**Type:** api
**Preconditions:** backend running.

**Steps:**
1. POST `/api/auto-sessions` with body omitting `natural_language` (and/or `symbol`).

**Expected outcome:** a 4xx with a clear validation message naming the missing field.
**Pass criteria:** status code is 4xx (400/422), NOT 500; response body contains a human-readable message identifying the missing field. No session created.

---

### TC-05 — Unbounded loop impossible: bad/absent `max_iterations` (error case + hard-budget anti-goal)

**Type:** api
**Preconditions:** backend running.

**Steps:**
1. POST with `budget:{"max_iterations":0}`.
2. POST with `budget` omitted entirely (otherwise valid pinned config).

**Expected outcome:** request (1) is rejected with 4xx; request (2) is either rejected OR accepted with a small safe default cap (never unbounded).
**Pass criteria:** case (1) → 4xx, no session runs; case (2) → either 4xx OR 200 where the resulting `autoRun.maxIterations` is a finite small number (e.g. ≤ a documented safe default) and the loop demonstrably terminates. Under no input does the loop run unbounded.

---

### TC-06 — Background run does not block the API event loop (anti-goal: non-blocking)

**Type:** api
**Preconditions:** TC-01 session is actively `running`.

**Steps:**
1. While that session's `autoRun.status` is `running`, issue 3 sequential `curl -sS -o /dev/null -w "%{time_total}\n" http://localhost:8000/api/sessions`.

**Expected outcome:** each `GET /api/sessions` returns 200 promptly while a backtest is in flight.
**Pass criteria:** every probe returns HTTP 200 and `time_total` < 3s (UI poll stays responsive; one-backtest-per-worker semaphore respected, event loop not blocked).

---

### TC-07 — `autoRun` status persisted to `session.json`, reflects last state on fresh read (TR-e + durable-persistence anti-goal)

**Type:** artifact
**Preconditions:** a tiny-budget session has reached a terminal state.

**Steps:**
1. Locate `<store>/<sessionId>/session.json` under `BACKTEST_STORE_DIR` (or durable default `…/.data/backtests`, never `/tmp`).
2. Read the `autoRun` block directly from disk (no server call).

**Expected outcome:** `session.json` contains `autoRun` with `status`, `stopReason`, `currentIteration`, `maxIterations`, `bestIterationId`, `startedAt`, `updatedAt`, and the on-disk values equal the terminal state (restart-survival proxy — durable file, not in-process/browser memory).
**Pass criteria:** `autoRun` block present in `session.json` on disk; `status` is a terminal value (`complete`/`stopped`) with a non-null `stopReason` and a non-null `bestIterationId`; store path is not under `/tmp`.

---

### TC-08 — Headless iteration artifacts match a manual run's `write_iteration` shape (TR-f + indistinguishable anti-goal)

**Type:** artifact
**Preconditions:** terminal tiny-budget session with ≥ 1 iteration.

**Steps:**
1. Inspect `<store>/<sessionId>/` iteration layout: `meta.json`, `strategy.py`, `insights.json`, `timeframes/<tf>/result.json`, `timeframes/<tf>/rating.json`, and `activity.jsonl`.
2. Compare key set against an existing manual-run session in the same store.

**Expected outcome:** the headless session's per-iteration files and the session/activity layout are the same schema a manual run produces — no parallel store, no schema fork.
**Pass criteria:** the same filenames/paths and node_dict key set (`id`, `prompt`, `scriptCode`/`strategy.py`, `strategyName`, `status`, `result`, `rating`, `insights`, `params`, `timestamp`, `parentId`) exist for the headless run as for a manual run; no extra/forked store directory was created.

---

### TC-09 — No secrets in activity log or session artifacts (anti-goal + error case)

**Type:** artifact
**Preconditions:** terminal tiny-budget session exists.

**Steps:**
1. `grep -rIE 'sk-[A-Za-z0-9]|OPENAI_API_KEY|ANTHROPIC_API_KEY|api[_-]?key' <store>/<sessionId>/` (incl. `activity.jsonl`, `session.json`, iteration files).

**Expected outcome:** no API key/secret values appear anywhere in the session's persisted artifacts.
**Pass criteria:** grep returns zero matches of real key material; no `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` value is written into `activity.jsonl` or any artifact.

---

### TC-10 — No schema/store fork, frozen contract untouched, no new infra (anti-goals)

**Type:** artifact
**Preconditions:** branch diff for this iteration available.

**Steps:**
1. `git diff --name-only main...HEAD` and confirm `apps/backend/shared/contracts.py` is unchanged.
2. Confirm new code is in `apps/backend/backend/auto_session.py` (+ optional `robust_objective.py`) and reuses `session_store.py`/`pipeline.py`; no new DB/queue/Celery/Redis dependency added (`apps/backend/requirements*.txt`/`pyproject` unchanged for infra).

**Expected outcome:** `contracts.py` untouched; new DTOs live in the new module; existing file store reused; no relational DB/SQLite/queue/broker introduced.
**Pass criteria:** `contracts.py` NOT in the diff; no new infra dependency; no parallel datastore directory or schema introduced.

---

### TC-11 — Loop terminates exactly on `max_iterations`, no extra round, `budget-exhausted` (TR-b)

**Type:** artifact
**Preconditions:** new pytest module `apps/backend/tests/test_auto_session.py` exists (LLM + Binance mocked).

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v -k "max_iteration or budget_exhaust"`.
2. Cross-check on a live tiny run (`max_iterations:2`): count iteration dirs in the store.

**Expected outcome:** the loop runs exactly `max_iterations` iterations (not one more) and ends with `autoRun.stopReason == "budget-exhausted"` when targets are never met.
**Pass criteria:** targeted pytest passes AND the live session has exactly `maxIterations` iterations with terminal `stopReason == "budget-exhausted"`.

---

### TC-12 — Loop terminates `criteria-met` when lenient targets satisfied (TR-c)

**Type:** artifact
**Preconditions:** test module present; lenient `targets` configurable.

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v -k "criteria_met"`.

**Expected outcome:** with targets satisfiable by iteration 1, the loop stops early with `stopReason == "criteria-met"` and does not exhaust `max_iterations`.
**Pass criteria:** targeted pytest passes; terminal `autoRun.stopReason == "criteria-met"` and `currentIteration < maxIterations` in that scenario.

---

### TC-13 — `bestIterationId` chosen by robust objective, not raw return (TR-d + best-by-robust anti-goal)

**Type:** artifact
**Preconditions:** test module present with a fixture where a high-raw-return but WFE-failing / over-leveraged candidate competes against a robust one.

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v -k "robust or best_selection"`.

**Expected outcome:** the iteration with the higher robust score (WFE ≥ threshold, min-trades floor met, drawdown/leverage penalized) is marked best; the higher raw-return but WFE-failing candidate is NOT selected.
**Pass criteria:** targeted pytest passes asserting `bestIterationId` == the robust candidate, explicitly NOT the higher-raw-return overfit candidate.

---

### TC-14 — One-iteration LLM/backtest failure → recorded failed iteration, loop still terminates (error case)

**Type:** artifact
**Preconditions:** test module present; failure injectable in one iteration.

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest tests/test_auto_session.py -v -k "failure or error_iteration"`.

**Expected outcome:** an LLM/backtest exception inside one iteration is captured as a failed iteration record; the loop continues/finishes and reaches a terminal state (no hang, no unhandled 500 that aborts the task).
**Pass criteria:** targeted pytest passes; the failing iteration is persisted with a failed status and the session still reaches a terminal `autoRun.status` (`complete`/`stopped`).

---

### TC-15 — Full backend suite green, no new regression (DoD + regression baseline)

**Type:** artifact
**Preconditions:** implementation complete.

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest tests/ -v 2>&1 | tee reports/qa/goal-auto-money-printer-iter-1-test.log`.

**Expected outcome:** all tests pass except the single pre-existing unrelated `tests/test_directions_cache.py::test_write_and_read_full_round_trip` failure (baseline 124 passed / 1 known fail).
**Pass criteria:** ≥ 124 passed; the ONLY failing test (if any) is `test_directions_cache.py::test_write_and_read_full_round_trip`; no other test newly fails; new `test_auto_session.py` cases pass.

---

### TC-16 — Dev handoff artifact present (DoD)

**Type:** artifact
**Preconditions:** dev step complete.

**Steps:**
1. Check `docs/handoffs/goal-auto-money-printer-iter-1-dev.md` exists and has the 5 required sections.

**Expected outcome:** handoff exists with What Was Built / Files Changed / Tests Run / Known Issues / Suggested Next Phase.
**Pass criteria:** file exists and is non-empty with all 5 sections.

---

### TC-17 — J-08: Track the automated run live in the UI (no manual reload)

**Type:** browser
**Preconditions:** backend :8000 + frontend :3000 running. Trigger a tiny-budget run via TC-01; capture `sessionId`.

**Steps:**
1. Chrome MCP → navigate to `http://localhost:3000`.
2. Open the session whose id == the TC-01 `sessionId` from the session list.
3. Without reloading the page, observe for up to ~120s.

**Expected outcome:** a run-status indicator shows "running"; ≥ 1 iteration appears with a backtest result + generated suggestions; the indicator then advances to a terminal state — all via live polling, no manual page reload.
**Pass criteria:** "running" indicator observed → at least one iteration card with result + suggestions rendered → terminal status shown, with NO manual page reload performed. Screenshot evidence saved under `reports/qa/goal-auto-money-printer-iter-1-evidence/`.

---

### TC-18 — J-09: Terminal stop reason visible + best iteration marked

**Type:** browser
**Preconditions:** the TC-17 session (or a fresh tiny-budget run with lenient targets) has reached terminal.

**Steps:**
1. In the UI, open the terminal session.
2. Read the displayed stop reason and locate the best-iteration marker.
3. If stop reason is `criteria-met`, read the best iteration's metrics and compare to the supplied `targets`.

**Expected outcome:** session shows a terminal status with a visible stop reason (`criteria-met` or `budget-exhausted`) and exactly one iteration visibly marked best; if `criteria-met`, the best iteration's metrics meet every supplied target.
**Pass criteria:** stop reason text is visible AND a single best-iteration badge/marker is shown; for `criteria-met`, best metrics satisfy every supplied robust target. Screenshot saved to the evidence dir.

---

### TC-19 — J-02: Opening a prior run re-binds the RIGHT analysis panel

**Type:** browser
**Preconditions:** ≥ 2 completed iterations/runs exist in history (use the headless run's iterations or run a manual backtest first).

**Steps:**
1. In the UI, with the latest run shown, note the RIGHT panel content (trades table rows + equity curve + walk-forward).
2. Select a *different, older* run from the history list.
3. Inspect the RIGHT panel (not just the LEFT conversation panel).

**Expected outcome:** the RIGHT analysis panel — trades table, equity curve, and walk-forward view — reloads to the selected older run's data, not the latest run's.
**Pass criteria:** after selecting the older run, the RIGHT panel trades table rows/equity curve visibly change to the selected run's values (a distinct trade count or first-trade timestamp from the latest run), confirming re-bind — not pinned to latest. Before/after screenshots saved to the evidence dir.

---

### TC-20 — Regression J-01 + J-06: NL backtest + warm-cache re-run

**Type:** browser
**Preconditions:** frontend + backend running.

**Steps:**
1. Enter "Buy when RSI crosses below 30, sell when it crosses above 70", set `BTCUSDT` / `1h` / `2024-01-01`→`2024-01-15` / capital `10000`, submit; wait for results.
2. Submit the identical strategy + same symbol/timeframe/date range again (warm cache).

**Expected outcome:** both runs render non-empty metrics, an equity curve, and a trades table; each adds a `run_id` to history; the second (warm-cache) run completes without error and without Binance re-fetch.
**Pass criteria:** run 1 shows metrics+equity+trades and a new history entry; run 2 also completes with metrics+equity+trades and a new history entry, no error surfaced.

---

### TC-21 — Regression J-03 + J-04: Walk-forward + AI insights

**Type:** browser
**Preconditions:** at least one completed run from TC-20.

**Steps:**
1. Open the completed run's detail; set IS/OOS windows; click "Run Walk-Forward".
2. On the same run, request AI insights.

**Expected outcome:** a WFE badge (green ≥0.5 / yellow 0.3–0.5 / red <0.3), a per-window table, and a combined OOS equity curve render; ≥ 1 ranked improvement suggestion renders (OOS-aware when WF data exists).
**Pass criteria:** WFE badge + per-window table + OOS equity curve all visible; at least one ranked suggestion rendered.

---

### TC-22 — Regression J-05 + legacy in-browser Auto Run not broken

**Type:** browser
**Preconditions:** fresh app load.

**Steps:**
1. Open `http://localhost:3000`; inspect the symbol and timeframe parameter controls.
2. Open a completed iteration and confirm the legacy in-browser "Auto Run" control is still present and starts its loop (do not run to completion — confirm it initiates, tiny/no budget).

**Expected outcome:** `/api/symbols` and `/api/timeframes` populate the controls; the pre-existing in-browser Auto Run still exists and is functional (coexistence expected this iteration — not a regression).
**Pass criteria:** symbol + timeframe dropdowns are populated (non-empty); the legacy in-browser Auto Run control is present and starts when clicked (no console crash). Screenshot saved to the evidence dir.

---

## Summary

Total test cases: 22
API tests: 6 (TC-01 – TC-06)
Artifact checks: 10 (TC-07 – TC-16)
Browser tests: 6 (TC-17 – TC-22)

**Traceability:** J-07 → TC-01/02/03; J-08 → TC-17; J-09 → TC-18; J-02 → TC-19;
regression J-01/J-06 → TC-20; J-03/J-04 → TC-21; J-05 + legacy auto-run → TC-22.
DoD backend new-tests (a)–(f) → TC-01/02 (a), TC-11 (b), TC-12 (c), TC-13 (d),
TC-07 (e), TC-08 (f). Error cases → TC-04/05/14/09. Anti-goals → TC-03 (lazy-load),
TC-05 (hard budget bounded), TC-06 (event loop), TC-07 (durable status), TC-08
(no schema fork / indistinguishable), TC-09 (no secrets), TC-10 (contracts frozen /
no new infra), TC-13 (best-by-robust). Regression baseline → TC-15. Handoff → TC-16.
