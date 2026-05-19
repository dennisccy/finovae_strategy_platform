# Phase goal-auto-money-printer-iter-5 — Implementation Summary

**Phase:** goal-auto-money-printer-iter-5
**Date:** 2026-05-19
**Written by:** developer

---

## Features Implemented

- **Learn-from-prior-runs warm start**: The second (and later) time the headless
  optimizer is run in open-universe mode, it now looks at how earlier runs performed
  and tries the historically strongest market/timeframe combinations **first**, so the
  cheap-first screening budget is spent where past payoff was highest.
- **Plain-language "why" note in the session feed**: When a warm start happens, the
  session activity feed shows one entry such as *"Warm start (global history):
  prioritising ETH/USDT 1h — prior best robust 0.78 across 1 prior session"*, so an
  operator can see exactly which past evidence drove the decision. It appears at the
  top of the feed and looks like the existing automated-run notes.
- **Opt-out switch**: Sending `history_scope: "this-run"` makes the run ignore all
  prior runs entirely — no learning, no "why" note, and the same fixed exploration
  order as before. Sending `history_scope: "global"`, omitting it, or sending anything
  unrecognised, all give the learning behaviour (the documented default).
- **Read-only and safe by construction**: Looking at prior runs never changes,
  renames, or deletes anything from those earlier runs. It is done once at the start
  of a run, off the main request-handling thread, so the UI and other requests stay
  responsive.

---

## Changed Behavior

- **`history_scope` request field**: Previously it was accepted and saved but had no
  effect. Now, on an open-universe run, it actually changes behaviour —
  `"this-run"` opts out of cross-run learning; anything else (including omitting it)
  enables the read-only warm start. The exact value the caller sent is still saved
  unchanged.
- **Open-universe exploration order**: Previously a fixed list every time. Now, when
  prior history exists and the run is not opted out, the same bounded list is
  **reordered** so the historically best families are screened/promoted first. With no
  usable prior history (or opted out) the order is exactly as before.
- **Session record**: An open-universe session now also records the *effective*
  history scope (`effectiveHistoryScope`) alongside the raw saved value. Pinned runs
  are completely unchanged.

---

## Backend-Only Items

- None. The one new piece of user-visible information (the warm-start "why" note)
  surfaces through the **existing** session activity feed with no UI code change —
  it renders exactly like the existing automated-run notes. Browser QA verifies it is
  visible on a global run and absent on an opted-out run.

---

## Incomplete Items

- None. All in-scope J-15 items from the phase spec are implemented and tested:
  read-only surrogate, effective `history_scope` semantics (global / this-run /
  default→global / garbage→default), stable bounded-seed reorder, the planner-decision
  citation, once-per-run off-thread execution, and all preserved invariants
  (no-history fallback, robust-best, pinned, budget).
- J-16 (deep overfit-gating demonstration / leaderboard) is intentionally **out of
  scope** for this iteration (next iteration); its robust-best invariant is only
  *preserved* here, not extended.

---

## Config and Environment Changes

- None. No new environment variables, settings, dependencies, datastores, queues, or
  migrations. Optimizer/history state continues to use the existing durable file
  store. Prior-run artifacts are read only, never altered.

---

## Known Limitations

- The "learn from prior runs" signal only considers **promoted, walk-forward-validated**
  iterations from prior open-universe runs (the trustworthy ones). Cheap screen-only
  results, failed iterations, and pinned-run iterations are deliberately not used as
  evidence.
- Reading a prior session that is corrupt or partially written is silently skipped
  (best-effort) so one bad folder can never stall a new run; such a session simply
  does not contribute to the warm start.
- "Strength" is a single robust score per market/timeframe family (the project's
  single-objective design); there is no multi-factor or exploration/bandit policy —
  just "try the historically strongest first", which is the intended scope.
- The only failing test in the backend suite is a pre-existing, unrelated
  directions-cache test that was already red before this iteration and is explicitly
  tolerated by the phase spec; nothing in this iteration touched that area.
