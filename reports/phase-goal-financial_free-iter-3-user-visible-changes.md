# Phase goal-financial_free-iter-3 — User-Visible Changes

**Phase:** goal-financial_free-iter-3
**Date:** 2026-05-23
**Written by:** ui-impact-analyst

---

## What Users Can Now Do

- Operators can now watch an automated session's **AI token spend against its cap** live in the automated-session status strip at the top of the Iterations panel (e.g. `1.2k / 50k tok`), updating on each ~2.5s poll while the run is active.
- Operators can now watch the automated session's **dollar cost against its cap** live in the same status strip (e.g. `$0.0123 / $0.0500`), so they can see what the search is spending as it spends it.
- Operators can now see, for an **open-universe** automated run, a **configurations-explored counter** (e.g. `1/2 configs`) in place of the rounds counter — showing how many distinct symbol/timeframe setups the search has tried out of its cap.
- Operators can now watch **distinct open-universe configurations stream in as iteration cards** (each card showing its own symbol/timeframe via its `params`), and see the single **Best** badge land on the best config by robust score across the run.

---

## What Changed in the Visible UI

- The **automated-session status strip** (`AutoSessionStatusStrip`) now shows three new counter chips in its right-aligned counter group: a token-spend chip (`… tok`), a USD-cost chip (`$…`), and — for open-universe runs — a configs chip (`…/… configs`). These sit alongside the existing wall-clock chip with `·` separators.
- For an **open-universe** session the strip shows a **`configs` counter instead of the `rounds` counter** (the choice is driven by whether the budget carries a `maxConfigs` value); pinned sessions are unchanged and still show `rounds`.
- When a run finishes at/near its cap, the strip wraps **amber** with a `Budget exhausted` badge and stop-reason label, and the new token/USD/configs counters inherit that terminal styling.

---

## What Old Behavior Changed

- **Starting an automated session without a symbol/timeframe (API):** previously rejected with a 400 ("open-universe not supported"). Now `POST /api/auto-sessions` with `objective: "robust"` + a valid `budget` and no symbol/timeframe returns **200** and launches an open-universe search. (This is an API-triggered behavior change — there is no in-UI control for it; see "Not Visible Yet".)
- **Automated-session status strip content:** the strip previously showed only `rounds` and elapsed wall-clock time. It now also shows token spend, USD cost, and (for open-universe runs) configs explored. The pinned-session display is otherwise unchanged.

---

## Not Visible Yet

- **Triggering an open-universe run from the UI** — the in-UI "Auto Run" control still starts only a **pinned-config** backend session. Open-universe runs can only be started via the API (`POST /api/auto-sessions` with no symbol/timeframe). The UI fully *tracks* such a run live (status, spend counters, streaming config cards) but cannot start one. Intentional per spec OUT OF SCOPE.
- **Per-config AI improvement suggestions** — open-universe configuration cards carry `insights: null` (a shape the UI already handles); they show the strategy, params, metrics, equity curve, and walk-forward result but not AI suggestions. Deferred to J-14.
- **Ranked candidate leaderboard** — only the single Best badge is shown; a ranked multi-candidate board is deferred to J-16.
