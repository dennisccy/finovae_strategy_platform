# Goal Iteration 2 — Wire reference-data endpoints into the parameter controls (J-05)

<!-- machine-readable goal-mode metadata -->
## Goal Mode Metadata

- **Session ID:** money-billions
- **Iteration:** 2
- **Mode:** next
- **Depth:** lean
- **Frontend Present:** yes
- **Target journeys:** J-05
- **Required-still-passing journeys:** J-01, J-02, J-03, J-04, J-06
- **Anti-goal reminders (verbatim from docs/goal.md):**
  - No hard-coded credentials, API keys, or tokens in source files (keys only via env / git-ignored `.env`).
  - The RestrictedPython sandbox MUST block file I/O, network, `exec`/`eval`, `__import__`, `open`, and `os`.
  - No lookahead: a generated signal must never observe future bars.
  - No nondeterministic backtests (slippage is seeded; identical inputs → identical output).
  - No dependency on a paid SaaS service other than Anthropic/OpenAI (already in Constraints).
  - The frozen dataclasses in `shared/contracts.py` must not be mutated in place.
  - OHLCV market data MUST be cached as a single Parquet file per (symbol, timeframe) — NOT one CSV or file per calendar day — and MUST NOT be re-fetched from Binance when a covering local cache exists.
  - `BACKTEST_STORE_DIR` (session/run history) MUST NOT default to a volatile `/tmp` path; session and run history MUST survive a process restart.
  - No relational database or SQLite is introduced for OHLCV, session, or directions storage (Parquet + durable file store only).
  - `GET /api/sessions/{id}` (the list/open path) MUST NOT eagerly parse full per-iteration `result.json`/`rating.json` payloads; iteration detail is lazy-loaded via the existing per-iteration endpoint.

## GOAL

When the user opens the app, the symbol and timeframe parameter controls are populated from the live `GET /api/symbols` and `GET /api/timeframes` endpoints instead of hardcoded frontend literals.

## BACKGROUND

J-05 is the only remaining failing Must-have journey and the critical path to GOAL_ACHIEVED (per the iter-1 evaluator recommendation). Both reference endpoints are already healthy and were confirmed in iter-0: `GET /api/symbols` returns `{"symbols": ["BTC/USDT", ... "PEPE/USDT"]}` (26 `BASE/USDT` strings) and `GET /api/timeframes` returns `{"timeframes": [{"value":"1m","label":"1 Minute"}, ... {"value":"1d","label":"1 Day"}]}` (6 objects). The failure is purely frontend: `apps/frontend/src/components/BacktestConfigBar.tsx` uses a hardcoded timeframe literal (`['1m','5m','15m','1h','4h','1d']`, line 61) and a free-text regex-validated symbol `<input>` (lines 43-55) — it never calls either endpoint. This is a small, isolated, low-risk frontend wiring change → **lean** depth, as the iter-1 evaluator recommended. The still-open eager-load anti-goal (`GET /api/sessions/{id}`, `session_routes.py:142-171`) and the J-04 "OOS-aware insights" soft gap are explicitly **deferred to a subsequent full-depth iteration** and are NOT in scope here; GOAL_ACHIEVED remains blocked until those are addressed in a later iteration even if J-05 passes here.

## IN SCOPE

### Backend
- [ ] None. No backend changes. `/api/symbols` and `/api/timeframes` are healthy and MUST NOT be modified (see NOTES — iter-0 lesson).

### Frontend
- [ ] On app load, fetch `GET ${API_BASE_URL}/api/symbols` and `GET ${API_BASE_URL}/api/timeframes` using the existing API-base convention (`const API_BASE_URL = import.meta.env.VITE_API_URL || ''`, mirroring the existing `/api/config` fetch at `apps/frontend/src/hooks/useBacktest.ts:447-453`).
- [ ] Populate the **timeframe** control from the `/api/timeframes` response (`value` drives selection, `label` available for display) instead of the hardcoded `['1m','5m','15m','1h','4h','1d']` literal at `BacktestConfigBar.tsx:61`.
- [ ] Populate the **symbol** control from the `/api/symbols` response so the user can pick from the fetched list (replaces the bare free-text input at `BacktestConfigBar.tsx:43-55` as the source of options).
- [ ] Provide loading and error/fallback states: while reference data is in flight the controls render in a sensible state; if either fetch fails, the controls fall back to safe working defaults so a backtest can still be run (J-01/J-06 must not break when the reference endpoints are momentarily unavailable).
- [ ] Preserve the currently-selected default (`BTC/USDT` symbol, `1h` timeframe as today): after wiring, the effective default selection that flows into a backtest run is unchanged.

### New user-facing capability
The user selects symbol and timeframe from server-provided reference data rather than typing/guessing; the available options reflect what the backend actually supports.

### New information displayed
The full server-supported symbol list (26 `BASE/USDT` pairs) and the six server-defined timeframes (with their human-readable labels) are visible in the parameter controls.

### New user actions
Symbol and timeframe are chosen from endpoint-backed controls (selectable list / options) instead of a hardcoded button row and an unconstrained free-text field.

### UI surface changes
`apps/frontend/src/components/BacktestConfigBar.tsx` only — the Symbol and Timeframe controls in the top parameter bar.

### Product surface delta
The parameter bar becomes data-driven and consistent with backend capabilities; the symbol field stops being an unguided free-text guess and the timeframe set is no longer a frontend duplicate of a backend list that could silently drift.

## OUT OF SCOPE

- Any backend change, including modifying `/api/symbols`, `/api/timeframes`, `/api/validate-symbol`, or `shared/contracts.py`.
- The `GET /api/sessions/{id}` eager-load anti-goal (`session_routes.py:142-171`) — deferred to a dedicated subsequent full-depth iteration.
- The J-04 "suggestions are OOS-aware when walk-forward data exists" soft-gap assertion — deferred to the same subsequent full iteration's QA.
- Reworking other controls in the bar (exchange, capital, dates, shorts, leverage, max-order, max-loss, auto-run) — leave untouched.
- Redesigning the parameter bar layout or visual style beyond what is required to render the endpoint-backed options.
- Adding a new reference endpoint or caching layer for reference data.

## DEFINITION OF DONE

- [ ] Target journey **J-05** passes via browser-qa-agent: with the app open, the symbol control offers the values from `/api/symbols` and the timeframe control's options come from `/api/timeframes` (verified against the live endpoint responses, not the old hardcoded set).
- [ ] Required-still-passing journeys remain green, verified by browser-qa-agent: **J-01** (run a backtest from NL with `BTC/USDT` `1h`) and **J-06** (warm-cache re-run) — highest regression risk because this change touches the exact controls they set; **J-02**, **J-03**, **J-04** confirmed not regressed.
- [ ] No anti-goal violation introduced (this is a frontend-only change; the storage anti-goals resolved in iter-1 and the deferred eager-load anti-goal must remain exactly as-is).
- [ ] `cd apps/frontend && npm run build` (tsc typecheck + Vite build) passes with no new errors; `npm run lint` is clean for the changed file.
- [ ] No backend code changed; backend test suite is unaffected (state this explicitly in the handoff rather than re-running it for a frontend-only change, unless any backend file was touched — in which case it must NOT have been).
- [ ] Reference-endpoint failure path verified: if `/api/symbols` or `/api/timeframes` is unreachable, the controls still allow a valid backtest with the existing defaults (no hard crash, no blank/unusable bar).
- [ ] Dev handoff written at `docs/handoffs/goal-money-billions-iter-2-dev.md`.

## TESTING REQUIREMENTS

- **Browser (browser-qa-agent):**
  - J-05 — open the app, inspect the parameter controls; assert the symbol options match the live `/api/symbols` payload and the timeframe options match the live `/api/timeframes` payload (capture evidence screenshot).
  - J-01 — submit a backtest with the endpoint-backed `BTC/USDT` `1h` selection; assert non-empty metrics, equity curve, trades table, and a new `run_id` in history.
  - J-06 — repeat the same symbol/timeframe/date-range run; assert the warm re-run completes and renders results and appears in history.
  - J-02 / J-03 / J-04 — smoke-verify still functional (open a prior run; run walk-forward; request insights) to confirm no regression from the control change.
- **Build/lint:** `cd apps/frontend && npm run build` and `npm run lint` (changed file) must pass.
- **Error cases:** simulate or reason through reference-endpoint failure (network error / non-200) — the symbol and timeframe controls must degrade to a usable default state, not break the page or prevent a backtest. The browser-qa or reviewer must confirm this fallback exists in code even if not separately exercised live.

## NOTES

- **Apply iter-0 lesson (Applies to: "any iter scoping J-05 — frontend-only; do not modify `/api/symbols`/`/api/timeframes`"):** J-05's failure is "the UI never calls healthy endpoints," NOT "broken endpoints." The endpoints return correct data; the fix is purely frontend wiring in `BacktestConfigBar.tsx`. The developer MUST NOT touch the backend reference endpoints. A green J-01/J-06 is independent of J-05 — do not assume wiring is correct just because a backtest still runs; J-05 requires the controls to be *populated from the endpoints*.
- **Format compatibility:** `/api/symbols` returns slash-form `BASE/USDT` (e.g. `"BTC/USDT"`), which matches the format the existing input already enforces (`/^[A-Z]+\/USDT$/`) and that the run pipeline already consumes for the currently-passing J-01/J-06. The value written into `params.symbol` / `params.timeframe` MUST stay in the exact string format the existing backtest request already uses — do not introduce a transform that changes what flows to `/api/run-backtest`.
- **Preserve existing capability without scope creep:** today the symbol field also accepts arbitrary user-typed `BASE/USDT` pairs validated via `/api/validate-symbol` (a non-journey capability). Replacing it with a strict closed dropdown would regress that. A native combobox (`<input>` + `<datalist>` populated from `/api/symbols`) keeps free-text entry while satisfying "populate the symbol control from `/api/symbols`," and a `<select>` (matching the existing Exchange `<select>` at `BacktestConfigBar.tsx:119-128`) is the simplest pattern if arbitrary entry is intentionally dropped. The decomposer recommends the combobox/`<datalist>` approach to avoid regressing arbitrary-symbol entry; the developer chooses the exact control but MUST satisfy the J-05 acceptance and the no-regression DoD items.
- **Fetch location:** `BacktestConfigBar` is currently presentational (props only). Two acceptable lean approaches: (a) fetch the two endpoints inside `useBacktest.ts` alongside the existing `/api/config` fetch (lines 447-453) and pass options down as props (consistent with the established pattern); or (b) a self-contained `useEffect`+`useState` fetch inside `BacktestConfigBar` (most surgical, no prop-drilling). Either is fine — pick the one that is the smaller, more consistent diff. Do not refactor unrelated code.
- **GOAL_ACHIEVED expectation:** even if J-05 passes here, the evaluator should still CONTINUE — GOAL_ACHIEVED remains blocked by the deferred `GET /api/sessions/{id}` eager-load anti-goal and the J-04 OOS-aware soft gap, both scheduled for a subsequent full-depth iteration. This iteration is intentionally narrow.
- iter-1's lesson (restart/persistence durability, `Path(__file__).resolve().parents[N]` defaults) does not apply to this frontend-only iteration.
