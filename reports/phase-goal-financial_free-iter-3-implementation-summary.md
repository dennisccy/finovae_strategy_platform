# goal-financial_free-iter-3 — Implementation Summary

**Phase:** goal-financial_free-iter-3
**Date:** 2026-05-23
**Written by:** developer

---

## Features Implemented

- **Open-universe automated search**: A single API call carrying only an objective and a budget
  (no symbol/timeframe) now starts a server-side search that tries **several different
  symbol/timeframe combinations** drawn from a small, fixed "seed universe" — instead of only
  refining one pinned setup. Each combination is fully evaluated and the single best one is marked,
  using the same robust (walk-forward-validated) quality measure as before.
- **Hard cost budget**: Every automated run is now bounded by real, enforced spending limits — a
  maximum number of AI tokens, a maximum US-dollar cost, a maximum number of configurations to
  explore, and a maximum wall-clock time. The run checks these limits **before** starting each new
  piece of work and stops the moment any limit is reached — it never takes "one more round."
- **Live cost visibility**: The automated-session status strip now shows, as the run progresses,
  how many AI tokens and how much money it has spent (each against its cap) and how many
  configurations it has explored — so an operator can watch what the search is spending as it spends
  it.
- **Real spend tracking**: Token usage reported by the AI provider is now captured and converted to a
  dollar cost using a single, central price list, rather than being merely logged and ignored.

---

## Changed Behavior

- **Starting an automated session without a symbol/timeframe**: Previously this was rejected with an
  error ("open-universe not supported yet"). Now it **starts an open-universe search** and returns
  success. (Providing both a symbol and a timeframe still runs the original single-setup refinement
  exactly as before — that path is unchanged.)
- **The "strategy idea" text is now optional for an open-universe run**: if you leave it out, the
  search draws a starting idea from its seed set; if you provide it, that idea is kept fixed and only
  the symbol/timeframe vary. (A fully-pinned run still requires a strategy description.)
- **Automated-session budget display**: the status strip previously showed only "rounds" and elapsed
  time. It now also shows token spend, dollar cost, and (for open-universe runs) configurations
  explored.

---

## Backend-Only Items

- **Open-universe runs can only be started via the API** (`POST /api/auto-sessions` with no symbol /
  timeframe) — there is intentionally no button in the interface to launch one this iteration. The
  interface fully **tracks** such a run live (status, spend counters, and the configuration cards
  stream in), but does not start one.

---

## Incomplete Items

- **Staged cheap-then-expensive screening (J-14)**: not in this iteration. Every explored
  configuration is currently evaluated to the full standard (including walk-forward). The per-config
  evaluation was deliberately written as one reusable step so a future cheap "screen first, promote
  the best" stage can wrap it without a rewrite.
- **Learning from past sessions (J-15)** and the **ranked candidate leaderboard view (J-16)**: not in
  this iteration (the single best is still marked; a ranked board is future work).

---

## Config and Environment Changes

- **None.** No new environment variables, no new datastore/queue, no schema changes. Token→dollar
  prices live in a single in-code price table (`shared/model_catalog.py`); update prices there.
  AI features still require `OPENAI_API_KEY` (default model) as before.

---

## Known Limitations

- **The developer did not run a live end-to-end open-universe search** (which would call the real AI
  provider and cost a small amount of money). It is fully covered by automated hermetic tests, and
  the new API behavior was confirmed live for all the request-validation cases (which run before any
  AI call). A tiny-budget live run is left for the QA step.
- **Open-universe runs always finish by reaching their budget** (or by being stopped) — there is no
  "targets met, stop early" path for them this iteration. The original single-setup runs keep their
  "targets met" early-stop behavior.
- **The seed universe is intentionally small and fixed** (a couple of liquid symbols × a couple of
  timeframes × a couple of starting ideas). The search will never fan out across the whole exchange;
  broadening it is future, history-justified work.
- **Open-universe configuration cards do not include AI improvement suggestions** (to keep cost low);
  they show the strategy, parameters, metrics, equity curve, and walk-forward result like any other
  card.
