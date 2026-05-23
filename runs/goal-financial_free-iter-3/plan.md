# goal-financial_free-iter-3 Execution Plan

**Goal-mode iteration 3 — Layer-2 start.** Target journeys **J-12** (open-universe multi-config
search from a bounded seed universe) + **J-13** (hard token/USD budget). Required-still-passing:
J-07–J-11 + no-regression J-01–J-06. Depth: full (backend loop + pipeline token threading +
frontend display). The spec is internally consistent and aligns with `docs/goal.md` and the
session blueprint — no drift (see Goal Alignment below).

## What to Build

**Backend (the bulk of the work):**
- **Accept open-universe on `POST /api/auto-sessions`.** When `symbol`/`timeframe` are omitted (with
  `objective: "robust"` + a valid `budget`), route to a NEW open-universe controller path instead of
  the current 400 (`auto_session_routes.py:199-207`). Keep the pinned-config path (both present)
  **byte-for-byte unchanged** so J-07 is untouched. `natural_language` becomes optional in
  open-universe mode (a seed idea is drawn from the seed universe when omitted; if provided it pins
  the idea and the universe varies symbol/timeframe).
- **Bounded seed universe** — an explicit, hard-capped constant in `auto_session.py`: a small set of
  liquid symbols × a few timeframes × 1–3 seed strategy ideas. The search enumerates a
  budget-bounded subset. MUST NOT enumerate `/api/symbols` or fan out exchange-wide.
- **Open-universe controller loop** — explore ≥2 distinct configs (differing symbol and/or
  timeframe); evaluate each through the existing `BacktestPipeline` (generate → backtest →
  walk-forward) and score with the existing `RobustScorer`; mark the single cross-config best as
  `autoRun.bestIterationId`. Reuse `_build_node` + `result_serialization.py` (no schema fork) and
  persist each config via `session_store.write_iteration` (lazy detail preserved). A single config's
  generation/backtest failure is non-fatal (logged, search continues). **Structure per-config
  evaluation as ONE reusable method** so J-14 can wrap it in stages later without a rewrite.
- **Hard budget — `max_configs` + token/USD.** Add `max_configs`, `configs_done`, `max_tokens`,
  `max_usd` to `BudgetTracker`; hard-enforce all in `exceeded()` (checked *before* starting each
  config/round — never "one more"). Add `with_config_completed()`. Wire `max_tokens`/`max_usd`/
  `max_configs` from the request through `_build_budget`. Add `configsDone`/`maxConfigs`/`maxTokens`/
  `maxUsd` to `to_dict()` (the tracker stays frozen — increments return new instances).
- **Real token/USD accounting (J-13).** Capture LLM token usage already present at the SDK response
  level in `script_generator.py:405` + `insights_generator.py:327` (today only `logger.info`'d) and
  thread it out of the pipeline's `generate_strategy`/`generate_insights` into the controller's
  `BudgetTracker.with_usage()`. Map tokens→USD via a NEW per-model rate table in `model_catalog.py`.
  Prefer real SDK usage over estimation. **DO NOT add token fields to `GenerateStrategyResult` /
  `shared/contracts.py` (frozen)** — use a side channel (e.g. a `last_usage` attribute on the
  generators that the pipeline reads after each call). Exact seam is the developer's call.
- **Both paths** check ALL hard caps (configs/iterations, tokens, USD, wall-clock) before each unit
  and finish `status="budget-exhausted"` / `stopReason="budget-exhausted"` when any cap is hit; no
  config/iteration appended after a cap.
- **Preserve B1+B2** — reuse `_save_auto_run`/`_stop_requested` under the shared per-session
  `asyncio.Lock`; no lock-free `autoRun` read-modify-write; store I/O off-loop via `_run_off_loop`;
  backtests stay semaphore-guarded.
- **Reuse the OHLCV Parquet cache across configs** (no re-fetch when a covering cache exists); skip
  re-backtesting an identical generated strategy by code hash.

**Frontend (display-only):**
- Surface **token + USD spend + configs-explored** in `AutoSessionStatusStrip` budget counters,
  read-only from `autoRun.budget` (`tokens`/`maxTokens`, `usd`/`maxUsd`, `configsDone`/`maxConfigs`),
  alongside the existing rounds + wall-clock. Display formatting only, no recomputation.
- Extend the `AutoRunBudget` TS type (`sessionApi.ts`) with the four new fields, mirroring the
  backend `to_dict()`.
- Open-universe configs render through the **existing** iteration cards (each already shows its
  `params` symbol/timeframe) — no new component, no new route.

## Agents Required
- developer: **yes** — backend (open-universe controller, budget hard-enforcement, token threading,
  model-catalog rates) + frontend (status-strip counters, TS type).
- backend-data: **yes**
- frontend-ux: **yes** (small, additive: counters in an existing strip + one TS interface)

## Frontend Present

Frontend Present: yes

## Files to Create/Modify

**Backend**
- `apps/backend/backend/auto_session.py` — extend `BudgetTracker` (`max_configs`/`configs_done`/
  `max_tokens`/`max_usd`, `with_config_completed`, hard-cap `exceeded()`, extended `to_dict()`);
  seed-universe constant; open-universe controller path + reusable per-config evaluation method;
  thread token usage into `with_usage`; preserve pinned J-07 path + B1/B2 lock + semaphore.
- `apps/backend/backend/auto_session_routes.py` — route open-universe (omitted symbol/timeframe) to
  the new path instead of 400; `natural_language` optional; `AutoSessionBudget` gains `max_configs`
  (gt 0); `_build_budget` wires `max_tokens`/`max_usd`/`max_configs`; keep pinned 200, bad-timeframe
  400, non-robust-objective 400.
- `apps/backend/shared/model_catalog.py` — NEW per-model token→USD rate table (additive; single
  source of truth; not a frozen contract).
- `apps/backend/strategy/script_generator.py`, `strategy/insights_generator.py` — expose captured
  SDK token usage on a side channel (keep existing logging).
- `apps/backend/backend/pipeline.py` — surface generator token usage from `generate_strategy` /
  `generate_insights` to the controller (no frozen-contract change).
- `apps/backend/tests/test_auto_session.py`, `tests/test_auto_session_routes.py` — new hermetic
  tests (see Key Test Scenarios); optional live key-gated open-universe smoke in
  `tests/test_auto_session_live.py`.

**Frontend**
- `apps/frontend/src/lib/sessionApi.ts` — add `maxConfigs`/`configsDone`/`maxTokens`/`maxUsd` to
  `AutoRunBudget`.
- `apps/frontend/src/components/AutoSessionStatusStrip.tsx` — render token/USD/configs counters.

**Docs**
- `runs/goal-session-financial_free/state/blueprint.md` — additive Notes edit only (Budget-counters
  row: token/USD hard-enforced + shown + `max_configs`/`configsDone`; reserve open-universe row as
  orchestration-only). No nav-skeleton change → **no `blueprint.reapproval-requested`**.
- `docs/handoffs/goal-financial_free-iter-3-dev.md` — dev handoff (required).

**Do NOT touch:** `shared/contracts.py` (frozen); no new datastore/queue/broker; no new endpoint.

## UI Evolution (Frontend Present: yes)
- **New user-facing capability:** trigger an open-universe search from one API call (objective +
  budget only) and watch ≥2 distinct configs stream in as iteration cards, stopping at a hard
  token/USD budget — with live token/USD spend now visible.
- **New information displayed:** token spend / USD cost (each vs its cap) and configs-explored count
  in the automated-session status strip; iteration cards for distinct open-universe configs.
- **New user actions:** none at the control level — J-12 is API-triggered; the in-UI "Auto Run"
  control stays pinned-config this iteration. The UI only **tracks** the open-universe run live.
- **UI surface changes:** status-strip budget counters extended with token/USD/configs. No new
  pages, panels, or routes.
- **Navigation changes:** none.

## Visual Requirements (Frontend Present: yes)
- **Component patterns:** reuse the existing `AutoSessionStatusStrip` counter row — same
  `text-xs text-slate-500` chips with `·` separators and `title` tooltips; no new component, no raw
  div-soup. Configs counter mirrors the `rounds` counter (`configsDone/maxConfigs configs`); token
  and USD chips show `spend / cap` (USD formatted, e.g. `$0.0123 / $0.05`; tokens compact, e.g.
  `1.2k / 50k tok`). Show `cap` only when present.
- **Layout:** unchanged two-panel workstation; counters sit in the existing right-aligned counter
  group at the top of the Iterations panel.
- **Key visual effects:** none new — follow the established light-theme status semantics already in
  `STATUS_META`.
- **States to handle:** active (running — counters accrue live via the existing ~2.5s poll of
  `GET /api/sessions/{id}`); terminal `budget-exhausted` (token/USD at/near cap, amber treatment);
  pinned sessions (no `max_configs`) must still render cleanly — omit the configs chip when absent.

## Key Test Scenarios

**Backend — hermetic, deterministic fake pipeline (existing `test_auto_session.py` pattern):**
- Open-universe controller explores ≥2 distinct configs from the bounded seed universe; best
  selected by `RobustScorer` across configs; terminal at `max_configs`.
- `BudgetTracker.exceeded()` returns True at the **token cap** and at the **USD cap** independently,
  evaluated *before* the next unit of work; no config/iteration appended after a cap.
- `max_configs=2` evaluates exactly ≤2 configs.
- Token/USD accounting threads real (faked) SDK usage into `with_usage`; **tokens→USD asserted to an
  exact value** against the model-catalog rate; tracker remains immutable.
- Pinned-config path (J-07) unchanged: `symbol`+`timeframe` present still runs the single-config
  improvement-rounds loop to its terminal state.
- Route matrix: open-universe `POST` (no symbol/timeframe) → **200** (not 400); pinned `POST` → 200;
  pinned + unsupported `timeframe` → 400; `objective != "robust"` → 400.
- B1+B2 race regression (`stop` vs `save` under the shared lock) stays green for the open-universe
  loop.
- **Error cases:** missing `budget` → 422; `max_configs`/`max_tokens`/`max_usd` ≤ 0 → 422; a single
  config's generation/backtest failure is non-fatal (search continues); a run where every config
  fails terminates cleanly (`budget-exhausted`) without crashing; **no API key/secret** ever appears
  in the activity log or `autoRun` block.
- Invariants stay green: `test_lookahead`, `test_determinism`, `test_sandbox`, and the existing
  auto-session suite. (Pre-existing red `test_directions_cache::test_write_and_read_full_round_trip`
  remains a non-blocking, untouched carry-forward.)
- Optional live key-gated smoke: one tiny real open-universe run to a terminal state if
  `OPENAI_API_KEY` is present.

**Browser QA (clear the accumulated live-pixel debt — iter-0/iter-2 lesson):**
- **J-08** + **J-10** on an open-universe run: live tracking (status strip updates incl. token/USD;
  cards stream without reload) + reload-mid-run survival.
- **J-01** + **J-05** manual regressions.
- **Health-check the Vite frontend is serving at the START and re-probe mid-window** (iter-2: it was
  up at QA start then went down). Aim for **real pixels this time**. Only if pixels blank under the
  documented Chrome-MCP hidden-tab render throttle, fall back to verifying via the exact backend
  endpoints the UI calls (`GET /api/sessions`, `GET /api/sessions/{id}` → `autoRun.budget`,
  `POST /api/auto-sessions`, `/stop`) — and say so explicitly.

## Assumptions (documented, not blocking)
- **Seed universe contents:** developer picks a small hard-capped set (≈2–3 liquid symbols × 2–3
  timeframes × 1–3 ideas) as an explicit constant in `auto_session.py`; never `/api/symbols`.
- **tokens→USD rates:** reasonable public list prices per model, defined once in `model_catalog.py`
  as the single source; tests assert against that constant (the rate IS the source of truth).
- **Token-threading seam:** generators expose last-call usage; the pipeline surfaces it to the
  controller without touching the frozen `GenerateStrategyResult` / `shared/contracts.py`.
- **`max_configs`** is meaningful only for open-universe; the pinned path keeps `max_iterations`
  unchanged.
- Tiny budgets throughout QA (≤2 configs/iterations, short date range, cheapest model, lenient
  targets) per the goal-doc rule for J-07–J-16.

## Goal Alignment & Scope Flags
- **Aligned, no drift.** J-12/J-13 are the next layered journeys in `docs/goal.md`; the blueprint
  already reserves the canonical homes (Budget-counters row + the Layer-2 open-universe row). The
  controller is **orchestration only** — no new canonical value, no second computing module, no
  second endpoint, no UI recomputation. Blueprint edits are additive → no re-approval.
- **Strictly out of scope (exclude):** J-14 staged SCREEN→PROMOTE (iter-3 evaluates every config
  *uniformly* through the existing pipeline incl. walk-forward — this is NOT a cheap SCREEN stage, so
  the "SCREEN-skips-WF" anti-goal is not triggered; do not half-build staging); J-15 global-history
  warm start; J-16 leaderboard UI; a UI control to trigger open-universe; any `shared/contracts.py`
  edit; any new datastore/queue/broker.
- **Anti-goal guardrails to enforce in review:** bounded seed universe (no exchange-wide fan-out);
  hard budget never takes "one more" past a cap; best by robust WFE-gated objective; Parquet cache
  reuse + code-hash dedup; same file store / no schema fork; B1+B2 non-blocking + persisted status;
  no secrets in artifacts; deterministic + no lookahead; frozen contracts untouched.
