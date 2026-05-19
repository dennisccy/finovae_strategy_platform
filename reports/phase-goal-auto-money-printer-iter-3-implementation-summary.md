# goal-auto-money-printer-iter-3 — Implementation Summary

**Phase:** goal-auto-money-printer-iter-3
**Date:** 2026-05-19
**Written by:** developer

---

## Features Implemented

- **Headless open-universe strategy search**: One API call with **no symbol
  or timeframe** — only an objective and a budget — starts an automated
  session that explores **several distinct market configurations** (different
  trading pairs / candle sizes) drawn from a small, fixed, built-in candidate
  list. The explored configurations show up live in the existing UI exactly
  like manually-run iterations, and the best one is flagged by the platform's
  existing robust (walk-forward, drawdown-aware) quality score.
- **Hard, tamper-proof spending limit**: Every automated run is now governed
  by an immutable cost tracker that simultaneously enforces a ceiling on AI
  tokens, US-dollar cost, number of configurations, and wall-clock time. The
  limits are locked the moment the run starts and cannot be raised while it
  runs. The run stops the instant a limit is reached — it never takes "one
  more round" past the cap.
- **Real spend accounting**: The actual token counts returned by the AI
  provider are captured and converted to a dollar figure using a built-in
  per-model price list. The recorded spend is saved with the session and
  shown in the UI.
- **Visible spend in the run status bar**: The existing automated-run status
  strip now shows how many AI tokens, dollars, and configurations were spent,
  and clearly marks a run that ended because it hit the budget (amber,
  distinct from a "targets met" or "stopped" finish).

---

## Changed Behavior

- **`POST /api/auto-sessions`**: Previously rejected any request that omitted
  symbol/timeframe with a 422 "not yet supported". Now, omitting **both**
  symbol and timeframe (with a valid objective + budget) starts an
  open-universe search. Supplying a pinned config still behaves exactly as
  before; a half-specified request (e.g. timeframe but no symbol) is still a
  clean 422; an unsupported objective or a malformed date is a clean 422
  (never a 500).
- **Every automated run (including the existing pinned runs)** now also
  records spend in its durable status and is bounded by the cost tracker.
  Default token/USD limits are deliberately high and finite, so a normal
  pinned run's behaviour and stopping point are unchanged — only an
  explicitly tiny budget changes when a run stops.
- **The chosen objective and the supplied history-scope are now saved with
  the session.** Both are written into the run's durable status block, so
  they survive a server restart / browser reload and are readable from
  `GET /api/sessions/{id}` — they are no longer merely validated and then
  forgotten. (`history_scope` is *recorded only*; it changes no behaviour
  this iteration — cross-run learning is a later iteration.)

---

## Backend-Only Items

- None. Every new capability is reachable: open-universe is API-triggered
  (no new UI control was requested — the spec explicitly says none), and the
  recorded spend and budget-exhausted reason are surfaced in the existing
  `AutoRunBar`.

---

## Incomplete Items

- None of the in-scope items are deferred. Explicitly **out of scope** per
  the spec and **not** built here: J-14 (staged SCREEN→PROMOTE / cheap-first
  routing), J-15 (global-history warm start, bandit/LLM planner, prompt-cached
  planner context, `history_scope` *learning* — `history_scope` is accepted &
  persisted only), J-16 (deep overfit-gating demonstration / leaderboard UI).

---

## Config and Environment Changes

- No new environment variables, datastores, queues, schedulers, or
  dependencies. `OPENAI_API_KEY` is still required for the real AI path
  (pre-existing; default model `gpt-5.4-mini`).
- New request fields (all optional, backward-compatible): `objective`
  (default `"robust"`; only `"robust"` supported), `history_scope` (accepted
  & persisted, no behaviour this iteration). New budget fields (all optional,
  safe-defaulted + hard-clamped): `max_ai_tokens`, `max_usd`, `max_configs`.
- The per-model USD price list lives in `shared/model_catalog.py` as a
  tunable static constant (not a paid pricing service).

---

## Known Limitations

- The open-universe search is a **deterministic enumerator** over a fixed
  6-entry seed list (a few liquid pairs × two timeframes). It does not yet
  learn which families to prioritise or expand the universe — that is the
  next iteration (J-15) and is intentionally not built here.
- When start/end dates are omitted for an open-universe run, a fixed short
  historical window (2023-01-01 → 2023-06-01) is used so the OHLCV Parquet
  cache can serve/reuse it cheaply across configs.
- The USD price list is representative public-list-style pricing; the dollar
  figure is exact with respect to that table, which is a constant a maintainer
  tunes — it is deliberately not a live price feed.
- Real-AI (live LLM) verification of J-12/J-13 is performed by browser-QA
  under the mandated tiny budget; unit tests exercise the real usage-capture
  path with a stubbed SDK client (no live tokens spent in CI).
- Pre-existing, out-of-scope test failure `test_directions_cache.py::
  test_write_and_read_full_round_trip` is unchanged (the only tolerated
  baseline failure; not touched by this phase).

---

## Post-QA Fix (round 1)

QA found one blocker: the `objective` and `history_scope` request fields
were *accepted* but **not persisted** — the spec requires them "accepted &
persisted". Fix: both are now saved into the run's existing durable status
block at session creation (reusing the existing session-store write — no
new storage, no format change, no architecture change). They survive a
restart/reload and appear in `GET /api/sessions/{id}`. Two regression tests
were added (asserting a fresh re-read and the API payload both carry the
values). Backend suite after the fix: **183 passed, 1 failed** — the one
failure is still only the pre-existing out-of-scope `test_directions_cache`
case (**zero new regressions**). No UI change was needed for this fix.
