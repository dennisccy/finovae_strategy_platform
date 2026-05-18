# goal-money-billions-iter-3 Functional Test Plan

**Phase:** goal-money-billions-iter-3
**Date:** 2026-05-18
**Frontend Present:** yes

## Phase Goal

Resolve the last open anti-goal: `GET /api/sessions/{id}` must stop eagerly parsing every iteration's full `result`/`rating` payload (lightweight list only); the frontend lazy-loads heavy detail on selection via the existing per-iteration endpoint, with loading/error states — and J-04 AI insights gets its first dedicated, distinct OOS-aware evidence (verification-only, no code change).

## Environment / Conventions

- Backend test command: `cd apps/backend && .venv/bin/python -m pytest tests/ -v`
- New backend test file (canonical anti-goal proof): `apps/backend/tests/test_session_routes.py`. Seed style must match `tests/test_session_store.py` (temp `BACKTEST_STORE_DIR` via `monkeypatch.setenv` + `importlib.reload`, real on-disk fixture, no store mocking; FastAPI `TestClient(backend.api.app)` or awaiting the `get_session` coroutine both acceptable).
- Live services: start with `./scripts/dev.sh`; backend/frontend run on deterministic offset ports — use the URLs the script prints. In steps below `$BE` = backend base URL, `$FE` = frontend base URL.
- J-04 insight regeneration requires `OPENAI_API_KEY` in the QA env (verification-only; capability already exists in `insights_generator.py` / `POST /api/generate-insights` — MUST NOT be modified).
- Anti-goal independence rule: J-02 passing does NOT prove the anti-goal resolved (J-02 passed every prior iteration *with* eager-load present). Resolution rests only on TC-01 (code) + TC-02 (response-shape test).

## Test Cases

### TC-01 — `get_session` no longer eager-loads iteration detail (code inspection)

**Type:** artifact
**Preconditions:** Implementation complete; `apps/backend/backend/session_routes.py` present.

**Steps:**
1. Open `session_routes.py`, read the `get_session` function (≈ lines 142-171).
2. Confirm the per-iteration loop calls `read_iteration_meta(...)`, not `read_iteration_full(...)`.
3. Grep the `get_session` body for `read_iteration_full`.

**Expected outcome:** `get_session` builds its iteration list from `read_iteration_meta`; `read_iteration_full` is not referenced inside `get_session` (it remains used only by `get_iteration`).
**Pass criteria:** Zero occurrences of `read_iteration_full` within `get_session`; iteration list sourced from `read_iteration_meta`; `meta`/`activityLog`/`backtestParams`/`selectedIterationId` and the 404 condition unchanged.

---

### TC-02 — `GET /api/sessions/{id}` returns NO heavy per-iteration payloads

**Type:** api
**Preconditions:** `test_session_routes.py` exists; a session with ≥1 **completed** iteration seeded (node carrying `result`, `rating`, `equity_curve`, `trades`).

**Steps:**
1. Run `cd apps/backend && .venv/bin/python -m pytest tests/test_session_routes.py -v`.
2. (Cross-check, live server) `curl -s $BE/api/sessions/<seeded_session_id> | python3 -m json.tool` after creating a completed run.

**Expected outcome:** Every entry in `iterationHistory` carries lightweight fields only; no heavy payload keys.
**Pass criteria:** For every `iterationHistory` entry, the keys `result`, `rating`, `equity_curve`, `trades` are **absent** (assert exact key absence — not present-but-null). HTTP 200.

---

### TC-03 — Lazy detail path intact: `GET /api/sessions/{id}/iterations/{iteration_id}` returns the full node

**Type:** api
**Preconditions:** Same seeded session/iteration as TC-02.

**Steps:**
1. In `test_session_routes.py`, for the same iteration assert the per-iteration endpoint/`read_iteration_full` returns the full node.
2. (Cross-check, live) `curl -s $BE/api/sessions/<sid>/iterations/<iter_id> | python3 -m json.tool`.

**Expected outcome:** The per-iteration response is the full `IterationNode` including `result` and `rating`.
**Pass criteria:** Response contains non-empty `result` and `rating` for the same iteration that was lightweight in TC-02. HTTP 200.

---

### TC-04 — `get_session` preserves meta/activity/params and lightweight-list fidelity

**Type:** api
**Preconditions:** Seeded session has `backtestParams`, `selectedIterationId`, ≥2 iterations, an activity log.

**Steps:**
1. Call `get_session` (test or `curl -s $BE/api/sessions/<sid>`).
2. Inspect `backtestParams`, `selectedIterationId`, `activityLog`, and the `iterationHistory` list.

**Expected outcome:** Non-iteration fields unchanged; lightweight list preserves order and the fields the frontend tree/selection needs.
**Pass criteria:** `backtestParams`, `selectedIterationId`, `activityLog` equal the seeded values; `iterationHistory` length and ordering match `list_iteration_dirs`; each entry includes `id`, `status`, `timestamp`, `params`, and the strategy name field.

---

### TC-05 — 404 behavior for non-existent session unchanged

**Type:** api
**Preconditions:** A session id known not to exist.

**Steps:**
1. `curl -s -o /dev/null -w "%{http_code}" $BE/api/sessions/does-not-exist-zzz` (and an equivalent assertion in `test_session_routes.py`).

**Expected outcome:** Same 404 behavior as before the change (only when no meta, activity, and iterations exist).
**Pass criteria:** HTTP `404` with detail `Session <id> not found`.

---

### TC-06 — Backend test suite green; pre-existing baseline failures documented

**Type:** api
**Preconditions:** All backend changes complete.

**Steps:**
1. `cd apps/backend && .venv/bin/python -m pytest tests/ -v 2>&1 | tee reports/qa/goal-money-billions-iter-3-test.log`.

**Expected outcome:** New `test_session_routes.py` passes; no new failures introduced.
**Pass criteria:** `test_session_routes.py` 100% pass; any failure (e.g. `test_directions_cache.py`) is byte-identical to HEAD and documented as pre-existing/out-of-scope in the dev handoff — not introduced by this iteration.

---

### TC-07 — Frontend typed lazy-fetch helper added

**Type:** artifact
**Preconditions:** `apps/frontend/src/lib/sessionApi.ts` present.

**Steps:**
1. Inspect `sessionApi.ts` for a GET sibling of `deleteIterationFromStore` (e.g. `fetchIterationDetail(sessionId, iterationId)`) hitting `GET /api/sessions/${id}/iterations/${iterationId}`.

**Expected outcome:** A typed function returns the full `IterationNode` (or null/error on failure).
**Pass criteria:** Function exists, targets the existing per-iteration endpoint, is typed to `IterationNode`, and is consumed by `useBacktest.ts`.

---

### TC-08 — Write-amplification guard on lazy-merged detail

**Type:** artifact
**Preconditions:** `apps/frontend/src/hooks/useBacktest.ts` present.

**Steps:**
1. Inspect the selection/hydration lazy-merge path in `useBacktest.ts`.
2. Confirm `savedIterationVersionRef` (and `savedActivityCountRef`) are updated when lazy `result`/`rating`/`insights` are merged into a node.

**Expected outcome:** Lazy-loaded detail does not trip the save effect into re-persisting an already-stored iteration.
**Pass criteria:** Code shows `savedIterationVersionRef` recomputed/updated on lazy merge so the save effect does NOT POST the merged node back to the store (no write-amplification).

---

### TC-09 — Detail-pane loading & error states exist

**Type:** artifact
**Preconditions:** `IterationPanel.tsx` / `SessionContainer.tsx` present.

**Steps:**
1. Inspect the detail pane components for an explicit loading indicator while the per-iteration fetch is in flight and an explicit error state on fetch failure.

**Expected outcome:** Detail pane never shows a silent blank panel during/after a lazy fetch.
**Pass criteria:** A visible loading indicator (spinner/skeleton) and a visible error message are rendered for the lazy fetch; history list/tree still renders against lightweight nodes (no assumption that `result`/`rating` exist pre-selection).

---

### TC-10 — J-02: open distinct prior run(s) from history → detail reloads via lazy fetch (PRIMARY regression watch)

**Type:** browser
**Preconditions:** `$FE` reachable; `$BE` running.

**Steps:**
1. Chrome MCP → navigate to `$FE`.
2. Submit a backtest (NL "Buy when RSI crosses below 30, sell when it crosses above 70", `BTCUSDT`, `1h`, a valid date range, capital 10000); wait for results. Repeat to create ≥2 runs.
3. Select an **earlier** run from the history list; then select a **different** run; then re-select the first.
4. Screenshot the detail view for each selection → `reports/qa/goal-money-billions-iter-3-evidence/TC-10-j02-<n>.png`.

**Expected outcome:** Each selected run's strategy spec, metrics, and trades populate the detail view (fetched lazily on selection), including on re-selection.
**Pass criteria:** For ≥2 distinct runs, detail shows non-empty strategy spec + metrics + trades table; switching/re-selecting never leaves a stale or blank pane.

---

### TC-11 — J-02 cross-layer: session-open network payload is lightweight

**Type:** browser
**Preconditions:** TC-10 setup; Chrome DevTools/network capture available.

**Steps:**
1. With ≥1 completed run, reload the session in the browser.
2. Capture the `GET /api/sessions/{id}` response in the network panel; inspect the `iterationHistory` entries.

**Expected outcome:** The session-open response is lightweight; heavy detail only arrives on the per-iteration request after selection.
**Pass criteria:** `GET /api/sessions/{id}` `iterationHistory` entries contain no `result`/`rating`/`trades`/`equity_curve`; a separate `GET /api/sessions/{id}/iterations/{iteration_id}` fires on run selection. (Corroborating signal, not a substitute for TC-01/TC-02.)

---

### TC-12 — J-04: dedicated, distinct OOS-aware insights evidence after walk-forward

**Type:** browser
**Preconditions:** A completed run; `OPENAI_API_KEY` set in QA env.

**Steps:**
1. From a completed run's detail view, run walk-forward (set IS/OOS windows, "Run Walk-Forward"); wait for WFE/per-window output.
2. Request/regenerate AI insights for that run.
3. Capture a **dedicated screenshot of the insights pane** (not the walk-forward panel) → `reports/qa/goal-money-billions-iter-3-evidence/TC-12-j04-insights.png`.

**Expected outcome:** ≥1 ranked suggestion explicitly references out-of-sample / walk-forward / WFE / robustness behavior.
**Pass criteria:** Insights pane shows ≥1 ranked suggestion containing OOS/walk-forward/WFE/robustness language. **The screenshot MUST be of the insights pane and visually distinct from the J-03 (TC-14) walk-forward capture — a duplicate of the walk-forward panel is INVALID and fails J-04.**

---

### TC-13 — J-01 smoke: NL run appends a new run_id to history

**Type:** browser
**Preconditions:** `$FE` reachable.

**Steps:**
1. Note current history count. Submit a fresh NL backtest (params as TC-10). Wait for results.

**Expected outcome:** Results panel renders metrics + equity curve + trades; a new entry appears in history.
**Pass criteria:** History gains exactly one new run with a distinct `run_id`; results panel non-empty.

---

### TC-14 — J-03 smoke: walk-forward renders WFE badge + per-window table + combined OOS curve

**Type:** browser
**Preconditions:** A completed run.

**Steps:**
1. Open the run detail, set IS/OOS windows, click "Run Walk-Forward".
2. Screenshot the walk-forward panel → `reports/qa/goal-money-billions-iter-3-evidence/TC-14-j03-walkforward.png`.

**Expected outcome:** WFE badge (green/yellow/red), a per-window table, and a combined OOS equity curve appear.
**Pass criteria:** All three elements render. Screenshot retained to confirm TC-12 (J-04) is a **distinct** image.

---

### TC-15 — J-05 smoke: symbol/timeframe controls populate from endpoints

**Type:** browser
**Preconditions:** `$FE` and `$BE` reachable.

**Steps:**
1. Load `$FE`; open the parameter controls; inspect the symbol and timeframe selectors.

**Expected outcome:** Selectors are populated from `/api/symbols` and `/api/timeframes` (non-empty options including `BTCUSDT` / `1h`).
**Pass criteria:** Both controls render non-empty option lists sourced from the endpoints; no empty/disabled control.

---

### TC-16 — J-06 smoke: warm-cache re-run is deterministic and appears in history

**Type:** browser
**Preconditions:** TC-13 completed for a fixed `BTCUSDT`/`1h`/date range.

**Steps:**
1. Re-run the same strategy with identical symbol/timeframe/date range/capital. Wait for results.

**Expected outcome:** Second run completes without error, renders metrics/equity/trades, and is added to history; identical inputs yield identical key metrics.
**Pass criteria:** Second run renders successfully, appears in history, and core metrics (e.g. total return, trade count) match the first run exactly (deterministic warm-cache path).

---

### TC-17 — Error case: per-iteration lazy fetch failure shows explicit error state

**Type:** browser
**Preconditions:** A session with ≥1 completed run open in the UI.

**Steps:**
1. Force the per-iteration fetch to fail (e.g. stop `$BE` after the session list loads, or block/return 500 for `GET /api/sessions/{id}/iterations/{id}` via DevTools network override).
2. Select a run from history.

**Expected outcome:** Detail pane shows a clear, visible error message; the history list remains rendered and usable.
**Pass criteria:** Explicit error state visible in the detail pane (no silent blank panel); session/history list still renders. Screenshot → `reports/qa/goal-money-billions-iter-3-evidence/TC-17-lazy-fetch-error.png`.

---

### TC-18 — Error case: selecting an iteration with no result does not crash detail

**Type:** browser
**Preconditions:** Session contains an in-progress/error iteration (no `result`) — e.g. submit a strategy that fails to compile, or an interrupted run.

**Steps:**
1. Select the no-`result` iteration from history.

**Expected outcome:** Detail view renders a benign state (status/empty), no exception, app stays interactive.
**Pass criteria:** No JS error/blank crash; detail pane handles the missing `result` gracefully; other runs remain selectable.

---

## Summary

Total test cases: 18

- API tests: 5 (TC-02, TC-03, TC-04, TC-05, TC-06)
- Browser tests: 9 (TC-10, TC-11, TC-12, TC-13, TC-14, TC-15, TC-16, TC-17, TC-18)
- Artifact checks: 4 (TC-01, TC-07, TC-08, TC-09)

**Binding gates:** TC-01 + TC-02 (code + response-shape) are the *only* proof of the eager-load anti-goal resolution — never inferred from J-02. TC-10 (J-02) is the primary regression watch. TC-12 (J-04) requires a dedicated insights-pane screenshot that is provably distinct from TC-14 (J-03) — a duplicate is invalid and fails J-04. TC-13/TC-14/TC-15/TC-16 confirm no regression in J-01/J-03/J-05/J-06.
