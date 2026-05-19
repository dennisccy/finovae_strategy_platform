# goal-auto-money-printer-iter-5 Dev Handoff

**Phase:** goal-auto-money-printer-iter-5
**Date:** 2026-05-19
**Agent:** developer
**Status:** complete

## What Was Built

J-15 — read-only global-history **warm start** + `history_scope` **opt-out** for the
headless open-universe optimizer. Deterministic read-only surrogate; **no LLM planner**
(spec's explicit core design — the acceptance is satisfiable deterministically and the
"never re-sent uncached every round" anti-goal is satisfied structurally by the
once-per-run guarantee, so there is no LLM call and no `cache_control` code is needed).

- **Read-only global-history surrogate** (`_mine_history`, `apps/backend/backend/auto_session.py`):
  mines the **existing** durable `session_store` for prior auto-sessions' **promoted,
  walk-forward-bearing** iterations (`stage == "promote"` AND non-null
  `walkForwardResult` AND a finite `robustScore`) and aggregates the **best robust
  score per `(symbol, timeframe)` family**. Uses only existing `session_store` read
  helpers (`list_iteration_dirs` + `read_iteration_meta`; enumerates `BASE_DIR/live`
  directly to avoid `derive_session_tabs`'s `_index.json` migration write — strictly
  read-only). Excludes the current run's own session (cross-run only). Best-effort: a
  missing/corrupt session or iteration is skipped (mirrors the SCREEN/PROMOTE `except`
  discipline) — it never raises out or hangs the run.
- **Effective `history_scope` semantics** (`_resolve_history_scope`): `"this-run"`
  (whitespace-tolerant) → **opt-out**; omitted / `null` / `"global"` / unknown-garbage
  → **`"global"`** read-only warm-start (the documented default; garbage is a clean
  default, never a 500). The **raw** supplied value still persists verbatim in
  `autoRun.historyScope` (null stays null); the **effective** value is recorded as the
  additive `autoRun.effectiveHistoryScope` key (no schema fork — mirrors iter-4's
  additive `stage`), **open-universe only**.
- **Warm-start reorder** (`_reorder_configs`): when effective scope is global, the
  bounded `_SEED_UNIVERSE` enumeration is returned as a **stable permutation** ordered
  by mined family strength (strongest historical family first; unseen/tied families
  keep the existing fixed seed order). It is always a permutation of the **same bounded
  set** — no new symbols/timeframes, no fan-out.
- **Planner-decision activity entry** (`_warm_start_configs`): exactly **one**
  `_activity("auto-run", …)` entry, emitted once before the SCREEN loop, citing the
  concrete prior evidence, e.g. *"Warm start (global history): prioritising ETH/USDT 1h
  — prior best robust 0.78 across 1 prior session"*. Plain operator language, **no API
  keys/secrets**, same entry shape the existing feed renders. Emitted only when
  warm-start is active AND usable prior history exists; **never** on `"this-run"` or an
  empty/no-promoted-history store (byte-identical no-warm-start fallback).
- **Once-per-run, off-thread**: the mine + reorder + citation runs **exactly once** per
  run via `asyncio.to_thread` (off the event-loop thread — iter-2 lesson), in
  `_run_auto_session_impl` immediately after `_config_plan` and before
  `_run_staged_open_universe`. Never recomputed per round/SCREEN/PROMOTE candidate.
- **Invariants preserved**: pinned path (J-07–J-11) byte-unchanged (no mining/reorder/
  citation/effectiveHistoryScope — open-universe-guarded); no-history fallback
  byte-identical to today's fixed seed order (J-12/J-13/J-14 unchanged);
  `select_best`/`robust_score` over **promoted** iterations untouched (warm-start
  changes SCREEN order, never selection — J-09/J-16 intact); cost tracker untouched (no
  LLM tokens added; `would_exceed` / `_SPEND_CAPS` / `max-configs` distinction
  unchanged); `shared/contracts.py`, `sandbox.py`, `pipeline.py`, `backtest/`,
  `session_store.py` **not modified** (verified empty git diff).

## Files Changed

- `apps/backend/backend/auto_session.py` — `_HISTORY_SCOPE_OPT_OUT`/`_GLOBAL`
  constants + `_resolve_history_scope`; `_mine_history` (read-only surrogate);
  `_reorder_configs` (stable bounded permutation); `_strongest_family` (deterministic
  citation pick); `_warm_start_configs` (once-per-run off-thread orchestrator);
  open-universe-only wire-in to `_run_auto_session_impl` (records
  `effectiveHistoryScope`, applies warm-start when global); loop init now also
  persists the raw `historyScope` (idempotent for the endpoint path — keeps the
  durable record coherent on direct invocation); corrected the two stale
  "`history_scope` learning is J-15 / OUT OF SCOPE" docs (`AutoSessionRequest`
  docstring + the accept-&-persist inline comment) to the new effective semantics.
- `apps/backend/tests/test_auto_session.py` — 12 new tests (pure-helper unit + awaited
  end-to-end behaviour) and 2 existing tests **consciously updated** (not loosened):
  `test_open_universe_objective_and_history_scope_persisted` and
  `test_history_scope_defaults_to_none_when_omitted` — persistence still asserted,
  new effective/opt-out behaviour now asserted, stale comments corrected.

## Frontend

**No frontend code was changed (verify-first, per plan).** The existing activity feed
renders the planner-decision entry with **zero changes**: `ActivityLogEntry.tsx`
renders an `auto-run` entry's `content` verbatim in a `<span>` with **no `truncate`**
(unlike `code-preview`), and `ActivityLog.tsx`'s `groupByIteration` routes entries with
a falsy `iterationId` to the **ungrouped** path — rendered at the **top** of the feed,
fully visible, not inside a collapsible accordion. The citation is emitted with an
empty `iterationId` so it renders identically to the iter-2/iter-4 `auto-run` markers
the feed already renders, at the top of the feed — UI-indistinguishable from a manual
run. Browser-QA is still **required** for J-15 (spec mandate): citation visible on a
`"global"` run, absent on a `"this-run"` run, screenshots. No `*-frontend.md` handoff
is written because no frontend code changed.

## Tests Run

Command: `cd apps/backend && .venv/bin/python -m pytest`
Result: **200 passed, 1 failed**

- `tests/test_auto_session.py`: **53 passed** (was 41 — +12 net new; 2 consciously
  updated; **zero regressions**).
- Full backend suite: **200 passed / 1 failed**. The single red is the pre-existing,
  out-of-scope, explicitly-tolerated `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
  (unchanged; `directions_cache.py`/`directions_routes.py` untouched). iter-4 baseline
  was 188 passed / 1 failed → **+12 passing, zero new regressions**.
- `ruff check backend/auto_session.py tests/test_auto_session.py` → All checks passed.
- `mypy backend/auto_session.py` → **zero** errors introduced in the iter-5-added code
  (the project gates on ruff, not mypy; 334 mypy errors are pre-existing project-wide
  noise unrelated to this change).
- Anti-goal proofs (all green, exact-value asserts):
  read-only content+mtime+file-set hash snapshot before/after run #2 byte-identical;
  opt-out invokes the miner **0** times and uses the byte-identical fixed seed order;
  reorder is a bounded-seed permutation (`set` equal); miner call-count **==1** per
  run; robust-best unchanged (history-favoured but WFE-failing promoted candidate is
  NOT best); garbage scope → clean default, no crash; corrupt prior session skipped,
  run still reaches a terminal state; no secrets in the citation.

## Known Issues

- None introduced. The only red in the suite is the pre-existing, out-of-scope
  `test_directions_cache::test_write_and_read_full_round_trip` (explicitly tolerated by
  the spec; not touched by this iteration).
- **No live external test applies**: this iteration adds **no** external calls — the
  surrogate is a deterministic read-only file-store mine with no LLM/network. Live
  behaviour is exercised by browser-QA under a tiny budget per the spec.
- The miner uses `read_iteration_meta` per iteration (each does its own dir scan →
  O(N²) over a session's iterations). Negligible for realistic sizes (a handful of
  sessions × tens of iterations) and chosen deliberately to use only the public
  read helpers (no reaching into store internals). Documented, not a blocker.

## Suggested Next Phase

iter-6 = **J-16** (deep overfit-gating stress demonstration / leaderboard). J-15 now
passes (pending review/QA/browser-QA); J-16 is the only remaining failing journey, so
per the agent rule the evaluator should still CONTINUE to iter-6 rather than declare
GOAL_ACHIEVED. Note the recorded outer-loop carryover (regenerate iter-4's two
transient UI-test-design stub artifacts) — that is outer-loop/orchestrator work, not
iter-5 code/test/journey work, and must not flip any verdict.
