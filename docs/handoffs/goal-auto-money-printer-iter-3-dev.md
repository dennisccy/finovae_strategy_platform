# goal-auto-money-printer-iter-3 Dev Handoff

**Phase:** goal-auto-money-printer-iter-3
**Date:** 2026-05-19
**Agent:** developer
**Status:** complete

## What Was Built

Optimizer Foundation — the indivisible J-12 (open-universe search) + J-13
(immutable hard cost tracker) slice.

- **Open-universe auto-session (J-12).** `POST /api/auto-sessions` with **no
  `symbol`/`timeframe`** — only `objective:"robust"` + a `budget` (optionally
  `history_scope`) — is now accepted and runs a server-side **deterministic
  bounded enumerator** over a small hard-coded **seed universe** (6 distinct
  `(symbol,timeframe)` entries; NOT the 26×6 grid, NOT env-driven, NOT a live
  exchange enumeration). Each config runs the existing
  generate→backtest(+walk-forward)→insights→record path and is written via the
  existing `write_iteration`/`_build_node`/`append_activity_entries` so a
  headless run is UI-indistinguishable from a manual one. The activity log
  records every explored config (`Exploring config N: SYM TF`).
- **Immutable hard cost tracker (J-13).** New `backend/cost_tracker.py`:
  monotonic/append-only spend, caps **fixed at construction** (frozen
  dataclass — no mutator), independently enforcing **AI-tokens / USD /
  max-configs / wall-clock** plus the existing `max_iterations` clamp. Checked
  **before each config/round** ("no one more round/config past the cap"): once
  any cap is reached no new config/round starts. A config already in flight
  completes its generate+insights calls, so worst-case overshoot is bounded to
  one config's remaining LLM call(s) — there is **no** within-round skip
  implemented (audit B2 correction; see audit report B1 for the bounded-
  overshoot gap and its correct follow-up fix). Absent/zero/negative caps →
  safe finite defaults (hard-bounded, never unbounded).
- **Real AI-token usage capture.** A dependency-free `shared/llm_usage.py`
  surfaces the **real** SDK `.usage` already read-and-discarded in
  `compiler.py` / `script_generator.py` / `insights_generator.py` into an
  optional caller-owned `usage_sink` (no `shared/contracts.py` change, no
  engine/sandbox touch). The auto-session loop drains it into the cost tracker
  — actual tokens, never an estimate/constant.
- **Per-model USD price table.** Static input/output USD-per-token constants
  in `shared/model_catalog.py` (the model single-source-of-truth, NOT
  `contracts.py`, NOT a pricing API). Unknown model → 0 USD but tokens still
  count, so the token cap stays binding; never crashes.
- **Budget-exhausted terminal + durable, visible spend.** On any hard cap the
  run reaches the existing terminal state with `stopReason="budget-exhausted"`,
  **no further config appended**, and the recorded spend (tokens/USD/configs/
  wall) is written into the durable `autoRun` block via the existing
  `_update_autorun` (no parallel store/schema fork) — survives restart+reload,
  readable from `GET /api/sessions/{id}`.
- **Best across configs by the robust objective.** Reuses `select_best`/
  `robust_score` over every completed config's `RobustInputs` — never raw
  return.
- **Frontend.** Additive spend readout in the existing `AutoRunBar`
  (tokens / USD / configs) and a visually distinct `budget-exhausted` terminal
  (amber + $ icon vs emerald criteria-met / red stopped). Type-only plumbing
  in `useBacktest.ts` — the iter-2 live-poll `try/finally` re-arm and the J-02
  heavy-detail merge precedence are byte-unchanged.

## Files Changed

- `apps/backend/backend/cost_tracker.py` — **NEW.** Immutable monotonic
  `CostTracker` + frozen `CostCaps` + safe-default/hard-ceiling resolution.
- `apps/backend/shared/llm_usage.py` — **NEW.** `capture_usage()` — real SDK
  `.usage` → caller sink (OpenAI/Anthropic normalised; best-effort, no-op
  without a sink).
- `apps/backend/shared/model_catalog.py` — `MODEL_PRICING` table +
  `model_token_prices()` + `usd_cost()` (unknown-model-safe).
- `apps/backend/backend/auto_session.py` — `objective`/`history_scope` on
  request; `max_ai_tokens`/`max_usd`/`max_configs` on budget; 422 gate relaxed
  for open-universe (partial pin still 422; bad objective 422; malformed dates
  422 not 500); `_SEED_UNIVERSE` + default window; `_config_plan`/`_Config`/
  `_build_cost_tracker`/`_drain_usage`; multi-config loop reusing the
  subprocess seam + `select_best`; per-cap budget-exhausted terminal + durable
  spend writes.
- `apps/backend/backend/pipeline.py` — forward optional `usage_sink` through
  `generate_strategy`/`generate_insights` (no engine/orchestration change).
- `apps/backend/strategy/{compiler,script_generator,insights_generator}.py` —
  optional `usage_sink` param; `capture_usage(...)` after the existing usage
  logging in both provider branches (no behavioural change without a sink).
- `apps/backend/tests/test_auto_session.py` — `FakePipeline` threads
  `usage_sink` (deterministic fake SDK usage); +9 tests (open-universe
  multi-config, robust-best-across-configs, max-configs cap, hard-token-budget
  real-usage + durable spend, subprocess distinct-pid multi-config, endpoint
  open accepted / bad objective 422 / partial dates 422, pinned-unchanged
  regression guard).
- `apps/backend/tests/test_cost_tracker.py`, `test_model_pricing.py`,
  `test_usage_capture.py` — **NEW** unit tests.
- `apps/frontend/src/hooks/useBacktest.ts` — `AutoRunSpend` type + optional
  `AutoRunStatus.spend` (type-only; poll logic untouched).
- `apps/frontend/src/components/SessionContainer.tsx` — additive `AutoRunBar`
  spend readout + distinct `budget-exhausted` styling.

## Tests Run

Command: `cd apps/backend && .venv/bin/python -m pytest`
Result: **181 passed, 1 failed** — the single failure is the pre-existing,
out-of-scope, baseline-documented `test_directions_cache.py::
test_write_and_read_full_round_trip` (baseline was 150 passed/1 failed →
**+31 new passing, zero new regressions**). `test_auto_session.py`: 35 passed
(was 26; the existing 26 all still green).

Lint: `.venv/bin/ruff check` on every changed/new file — new files clean;
the 4 touched generator/pipeline files have **no new** errors (pre-existing
ruff debt is unchanged / slightly reduced; not in scope to fix per the
surgical-changes rule).

Frontend: `cd apps/frontend && npm run build` → **EXIT 0** (tsc + vite; the
>500 kB chunk warning is pre-existing, not an error).

Service startup: backend boots clean (`Application startup complete`, no
tracebacks); live smoke `POST /api/auto-sessions` open-universe → **200**,
bad objective → **422**. All test server processes killed; port free.

## Known Issues

- **J-12/J-13 live (real-LLM) verification is browser-qa's job** under the
  tiny-budget mandate (cheapest model, short window, `max_configs:2`). The
  real-LLM path requires `OPENAI_API_KEY` (pre-existing constraint, default
  model `gpt-5.4-mini`); the backend boots without it but the generate/
  insights calls fail without a key. No NEW external system was introduced
  (the price table is a static constant by design, not a pricing API), so
  there is no new live integration to validate at the unit level — the real
  SDK `.usage` capture path is unit-tested with a stubbed SDK client and
  exercised end-to-end by browser-qa under a tiny budget.
- `MODEL_PRICING` USD values are representative public-list-style constants
  (developer's choice per the spec). USD spend is exact w.r.t. the table; the
  table itself is a tunable constant, intentionally not a live price feed.
- Pre-existing out-of-scope failure `test_directions_cache.py::
  test_write_and_read_full_round_trip` remains (untouched; the only tolerated
  failure per the spec baseline).

## Suggested Next Phase

J-14 (staged SCREEN→PROMOTE / cheap-first model routing): introduce a cheap
SCREEN stage that does NOT run walk-forward or the strongest model, promoting
only the top-k survivors to the full pipeline — building directly on this
iteration's bounded enumerator + cost tracker (the hard budget already caps
total spend, so SCREEN is a pure efficiency gain). J-15 (global-history warm
start + prompt-cached planner + `history_scope` learning) and J-16 (deep
overfit-gating stress demonstration / leaderboard) follow.

---

## Fix Notes — QA FAIL round 1 (TC-07)

**Date:** 2026-05-19 · **Agent:** developer · **Mode:** FIX MODE

**Single blocker fixed:** TC-07 — `history_scope` (and `objective`) were
*accepted* (POST → 200) but **never persisted**. The spec IN SCOPE, the
execution plan, and test-plan TC-07 all require them "accepted **&
persisted**"; only the accept half was implemented. `req.history_scope`
was referenced solely at the `AutoSessionRequest` field + docstring;
`req.objective` was validated but discarded. Absent from `session.json`,
from `GET /api/sessions/{id}`, and from iteration meta.

**Root cause:** `create_auto_session`'s initial `write_session_meta` wrote
`name`/`lastAccessedAt`/`backtestParams`/`autoRun` but never recorded the
two accepted request-config fields.

**Fix (minimal, in-scope, zero anti-goal risk — exactly QA's suggested
fix):** persist `objective` and `historyScope` into the **existing durable
`autoRun` block** via the **existing** `session_store.write_session_meta`
call in `create_auto_session` (`auto_session.py`). No new store, no schema
fork, no `shared/contracts.py`/sandbox/engine/orchestration change, no new
infra. `_update_autorun_sync` is a read-merge-write that only `.update()`s
explicit per-round `changes` (which never include these keys), so both keys
are preserved verbatim across every loop write and survive a worker
restart + browser reload. `GET /api/sessions/{id}` already returns the full
`autoRun` block verbatim (`session_routes.py:185`, byte-unchanged), so the
values surface in the API payload with no route change. `history_scope`'s
cross-run *learning* remains J-15 / OUT OF SCOPE — the value is persisted
only; it is read by nothing in the loop (the controller is still the
deterministic bounded enumerator; no cross-run mining/mutation added).

**Files changed in this fix:**
- `apps/backend/backend/auto_session.py` — added `"objective": objective`
  and `"historyScope": req.history_scope` to the initial `autoRun` block in
  `create_auto_session` (the only behavioural change; ~2 lines + comment).
- `apps/backend/tests/test_auto_session.py` — **+2** regression tests:
  - `test_open_universe_objective_and_history_scope_persisted` — POST with
    `history_scope:"this-run"` → asserts a **fresh on-disk re-read**
    (`ss.read_session_meta`, the exact restart/reload path) carries
    `autoRun.objective == "robust"` **and** `autoRun.historyScope ==
    "this-run"`, **and** that `GET /api/sessions/{id}` exposes both. This is
    the spec-mandated "re-read of session meta carries the supplied
    history_scope" assertion; it FAILS by construction if the fix is
    reverted (verified RED → GREEN).
  - `test_history_scope_defaults_to_none_when_omitted` — omitted
    `history_scope` persists as `null`; `objective` still defaults to and
    persists `"robust"`.

**TDD evidence:** new tests written first, confirmed **RED**
(`KeyError: 'objective'` — accepted but not persisted), fix applied,
confirmed **GREEN**.

**Tests after fix:** `cd apps/backend && .venv/bin/python -m pytest -q` →
**183 passed, 1 failed** — the single failure is still **only** the
pre-existing out-of-scope `test_directions_cache.py::
test_write_and_read_full_round_trip` (QA baseline was 181 passed/1 failed →
**+2 new passing, ZERO new regressions**). Targeted iter-3 suites
(`test_auto_session test_cost_tracker test_model_pricing
test_usage_capture`): **59 passed** (was 57, +2). No frontend file was
touched in this fix (the existing frontend handoff stays valid; the two new
keys are inert extra fields the `AutoRunBar` never reads → no NaN/undefined
risk, TC-14 still holds).
