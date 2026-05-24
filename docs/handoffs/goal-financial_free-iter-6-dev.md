# goal-financial_free-iter-6 Dev Handoff

**Phase:** goal-financial_free-iter-6
**Date:** 2026-05-24
**Agent:** developer
**Status:** complete

## What Was Built

J-15 — **global-history warm start for the open-universe search, opt-out-able**
(a RE-LAND of the iter-5 design that was lost in a discarded worktree). Backend-only;
reuses the existing `auto-run` Activity-Log render path (zero new frontend code).

- **Request + config plumbing.** `POST /api/auto-sessions` now accepts an optional
  `history_scope` field, validated to `{"global", "this-run"}` with a **422** on any
  other value, **default `"this-run"`** (the opt-out — today's behavior). Threaded
  through `_build_config` → a new frozen `AutoSessionConfig.history_scope` field. The
  pinned path (`_run_inner`) ignores it.
- **Read-only history miner** (`mine_history_families` in `auto_session.py`). Scans
  prior sessions (excluding the in-flight one and any still-running session) using only
  the lightweight read APIs (`derive_session_tabs`, `read_session_meta`,
  `read_iteration_meta` — **never** the heavy `result.json`/`rating.json`), scores each
  prior iteration with the ONE canonical `RobustScorer`, and returns the strongest
  (max-score) result per `(symbol, timeframe)` family. Strictly read-only.
- **Cached LLM-planner** (`apps/backend/strategy/history_planner.py`, mirroring
  `InsightsGenerator`). Given the mined leaderboard + the bounded seed families, it
  returns a prioritized seed-family ordering + a one-line rationale citing a prior
  session/family/score. Its Anthropic system prompt carries
  `cache_control: {"type": "ephemeral"}` (prompt-cached). Invoked through the shared
  `BacktestPipeline.plan_warmstart(...)` which exposes `last_planner_usage` for budget
  accounting. Best-effort: any failure (no key / SDK error / malformed output) raises
  and the loop falls back to the deterministic mined-family ordering.
- **Warm-start ordering in `_run_open_universe`.** When `history_scope == "global"` and
  at least one prior in-seed family exists: mine (read-only) → run the planner (≤ once
  per run, before SCREEN, token usage threaded into the budget) → emit **one**
  `auto-run` planner-decision Activity-Log entry (`WARM-START — prioritizing … (prior
  session …: robust score …)`, no secrets) → reorder the bounded seed so the
  historically-strongest in-seed family is screened first → rank PROMOTE by
  `(history_priority, screen_score)` so that family is promoted first. Best stays
  `RobustScorer.select_best(promoted)` (unchanged, WFE-gated). For `this-run` / the
  omitted default / any unexpected value, mining + planner + citation are skipped
  entirely and the SCREEN ordering + PROMOTE ranking are byte-for-byte today's
  deterministic behavior.
- **Budget compliance.** The planner counts against the immutable `BudgetTracker`
  (token/USD) before SCREEN; a pre-exhausted cap terminates `budget-exhausted` before
  the planner and before SCREEN.

## Files Changed

(Matches `git diff --name-only HEAD -- apps/`.)

- `apps/backend/strategy/history_planner.py` — **NEW.** Cached LLM history-planner
  (ephemeral `cache_control` system prompt, `last_usage` side channel, OpenAI + Anthropic
  paths, deterministic-fallback contract).
- `apps/backend/backend/auto_session.py` — **MODIFIED.** `AutoSessionConfig.history_scope`
  field; `FamilyHistory` + `mine_history_families` read-only miner; `order_families_by_history`,
  `coerce_family_order`, `reorder_configs_by_family`, `history_brief` helpers; the `global`
  warm-start branch + `_warm_start` controller method in `_run_open_universe`; history-aware
  PROMOTE ranking.
- `apps/backend/backend/auto_session_routes.py` — **MODIFIED.** Validated `history_scope`
  request field (422 on invalid, default `this-run`) threaded through `_build_config`.
- `apps/backend/backend/pipeline.py` — **MODIFIED.** `HistoryPlanner` instance,
  `last_planner_usage` side channel, and `plan_warmstart(...)` (mirrors `generate_insights`).
- `apps/backend/tests/auto_session_helpers.py` — **MODIFIED.** Extended the shared
  `FakePipeline` with `plan_warmstart` (configurable order/rationale/usage/raise) +
  `last_planner_usage` (additive; existing tests unaffected).
- `apps/backend/tests/test_history_warmstart.py` — **NEW.** 20 hermetic J-15 tests
  (warm-start citation + first-promoted-family match, opt-out no-citation, read-only
  byte-identical mining, meta-only mining, planner ≤ once + token threading, pre-exhausted
  budget, empty store, bounded seed, single-scorer coherence, no-secrets, planner
  prompt-cache marker + malformed-output fallback).
- `apps/backend/tests/test_auto_session_routes.py` — **MODIFIED.** Added route tests:
  `history_scope` global/this-run/omitted accepted 200, invalid value → 422.

## Tests Run

Command: `cd apps/backend && .venv/bin/python -m pytest`
Result: **231 passed, 1 failed, 2 deselected.**

- The single failure is the **pre-existing, out-of-scope** red named in the spec:
  `tests/test_directions_cache.py::test_write_and_read_full_round_trip` (Capability #10,
  untouched — not in this diff).
- New J-15 tests: `tests/test_history_warmstart.py` — 20 passed.
- No-regression: `tests/test_auto_session.py` (J-07–J-14) + `tests/test_auto_session_routes.py`
  all pass; the J-12/J-13/J-14 hermetic tests (which set no `history_scope`) pass **unchanged**
  under the new `this-run` default.

Lint/type (changed files): `ruff check` — clean on all files I created/modified (the 15
pre-existing `pipeline.py` ruff items and the project-wide `mypy --strict` debt are not in
my diff and were not touched — `mypy` error counts for `auto_session.py` (27) and `pipeline.py`
(18) are unchanged from HEAD; `history_planner.py`'s only remaining mypy items are the same
anthropic/openai SDK-stub `union-attr`/overload artifacts the sibling `insights_generator.py`
already carries).

## Persistence Gate (DoD-0 — the single reason iter-5 failed)

Verified BEFORE writing this handoff, against the real working tree (no isolated worktree
was used — all work was done directly in the pipeline tree):

- `git diff --stat HEAD -- apps/backend/` is **non-empty** (7 files, +1123/−9) and includes
  all four required paths: `strategy/history_planner.py` (new), `backend/auto_session.py`
  (modified), `backend/auto_session_routes.py` (modified), `tests/test_history_warmstart.py` (new).
  The two new files were marked `git add -N` (intent-to-add) so they are visible to
  `git diff HEAD` (untracked files otherwise do not appear).
- `test -f apps/backend/strategy/history_planner.py` succeeds; `grep -rl history_scope
  apps/backend/backend/` returns `auto_session.py` and `auto_session_routes.py`.
- `runs/goal-financial_free-iter-6/status.json` has non-empty `changed_files` and `tests_run: true`.
- This handoff's "Files Changed" list matches `git diff --name-only HEAD -- apps/`.

## Known Issues

- **Pre-existing red (out of scope):** `tests/test_directions_cache.py::test_write_and_read_full_round_trip`
  fails on HEAD too (directions cache, Capability #10) — untouched by this iteration.
- **Pre-existing flake (out of scope):** `tests/test_auto_session_routes.py::test_post_returns_before_loop_completes_and_get_stays_responsive`
  is a timing-race test on the **pinned** path (no `history_scope`) — it passed in the full-suite
  run but fails intermittently in isolation (~1/3). Named in the spec NOTES as a de-flake-opportunistically
  item; my warm-start changes cannot affect it (pinned runs never invoke the planner).
- **Live key-gated run not executed:** per the spec, J-15's display aspect is closed at the
  endpoint layer (`GET /api/sessions/{id}.activityLog` + per-iteration meta) — the documented
  Chrome-MCP headless-throttle substitute and sufficient because J-15 adds zero new FE render
  path. The optional live OpenAI+Binance run pair (≥ 9-month range) was not run (no key configured
  in this environment); it remains available behind `pytest -m integration`-style manual execution.
- **Planner gating nuance (documented assumption):** the planner + citation run only when at
  least one **in-seed** family has prior history (not merely any prior family). This avoids a
  wasted LLM call and a citation with no in-seed score to cite when prior runs explored only
  out-of-seed families; warm-start still degrades to the deterministic (grid) order with no
  citation in that case.
- **File size:** `auto_session.py` grew to ~1.3k lines (the miner co-locates with the one
  `RobustScorer`/`IterationMetrics` it reuses, avoiding an import cycle a separate
  `history_mining.py` would create). Noted for future refactor; not a functional issue.

## Suggested Next Phase

**J-16** — the overfit-gating multi-candidate leaderboard UI — is the only must-have journey
remaining before GOAL_ACHIEVED. After J-15 lands green and persists, J-16 is all that's left.
