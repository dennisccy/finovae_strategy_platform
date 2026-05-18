# Phase goal-money-billions-iter-3 — What to Click (Operator Verification Guide)

**Phase:** goal-money-billions-iter-3
**Time required:** ~5 minutes
**Written by:** ui-test-designer

---

## Prerequisites

- Backend + frontend running (`./scripts/dev.sh` from the repo root).
- Frontend reachable at **http://localhost:3691**.
- A session that already has **at least 2 completed runs**. If you do not have
  one, do step 2 below twice first (each NL run takes ~10–30 s), then continue.
- (Only for step 8 / J-04) the backend has `OPENAI_API_KEY` set.

> This is a single-page app — there is no per-feature URL. Everything happens
> on the one page at `http://localhost:3691`. The **left** panel is the
> strategy/activity area; the **right** panel is the run history + detail.

---

## Verification Steps

1. Open **http://localhost:3691**.
   - **Expect:** Header shows **"Finovae Strategy Platform"** and a grey
     **"Sessions"** button; a config bar (Symbol / Timeframe / …) and two
     panels render. No blank page, no red error overlay.

2. In the left panel textarea type
   `Buy when RSI crosses below 30, sell when it crosses above 70`, set
   **Symbol** = `BTC/USDT`, **Timeframe** = `1h` in the config bar, then click
   the blue **Send** button (paper-plane icon, bottom-right of the left panel).
   - **Expect:** A new run appears in the right panel; when it finishes its
     card shows status **"Complete"** and a metrics row like
     `+x.xx% | N trades | DD -x.x% | WR x% | SR x.xx`. The right-panel header
     count **"Iterations (N)"** increased by 1 (confirms J-01 still works).

3. Click the grey **"Sessions"** button in the header, then click the current
   session row, and if a run's detail is showing click **"Back to history"**
   so the right panel shows the run list with **nothing selected**.
   - **Expect:** The right panel shows **"Iterations (N)"** and each completed
     run's card already shows its full metrics row **without you clicking it**
     (metrics come from the lightweight open response — this is the changed
     behaviour).

4. In the right panel, click an **older** completed run card (a compact row).
   - **Expect:** Briefly a centered spinner with **"Loading run detail…"** /
     "Fetching this run's strategy, metrics, and trades.", then it is replaced
     by the full detail: an **Equity Curve** chart and a **"Trade History (N
     trades)"** table with rows. (On a fast local backend the spinner can flash
     by quickly — that is fine; a *stuck* spinner or a blank pane is **broken**.)

5. Click the top-left back arrow (or **"Back to history"**), click a
   **different** completed run, then go back and click the **first** run again.
   - **Expect:** Each run shows its **own** strategy name, return badge, and
     trade count every time — never another run's data, never a blank or
     perpetually-spinning pane. (This is the primary J-02 regression check.)

6. With a completed run's detail open, press **F5** to reload the page.
   - **Expect:** After a brief load the right panel **automatically re-renders
     that same run's detail** (Equity Curve + Trade History) without you
     clicking anything — the restored selection auto-loads.

7. In the open run's detail, find **"Walk-Forward Analysis"**, set
   **"IS months"** = `6` and **"OOS months"** = `3`, click
   **"Run Walk-Forward"**, and wait.
   - **Expect:** A green/yellow/red **`WFE x.xx`** badge, a per-window table,
     and a combined out-of-sample equity curve appear (confirms J-03 still
     works with lazy-loaded strategy code).

8. (J-04) After the walk-forward completes, trigger an AI-insights
   request/regenerate for this run as described in the functional test plan
   **TC-12**, then look at the **left** panel.
   - **Expect:** A blue box with a 💡 lightbulb icon appears in the **left**
     panel with suggestion pill buttons; **at least one** suggestion title or
     the summary references **out-of-sample / walk-forward / WFE / robustness**.
     The J-04 screenshot must be of **this left-panel 💡 box** and must be
     visually **distinct** from the right-panel Walk-Forward panel in step 7.

---

## What "Working Correctly" Looks Like

- The run-history list and each card's metrics row appear **immediately** on
  session open, before any run is clicked.
- Clicking a run shows a brief "Loading run detail…" spinner, then the full
  Equity Curve + Trade History for **that** run.
- Switching between runs and reloading the page always shows the correct run's
  detail — never stale, blank, or perpetually loading.
- A fresh NL run still appears in history and walk-forward still renders its
  WFE badge/table/curve.
- After walk-forward + regenerate, the left-panel 💡 box has an
  OOS/walk-forward-aware suggestion.

## Common Issues

- **Detail pane stuck on the spinner or blank after clicking a run:** the lazy
  per-iteration fetch failed or never resolved. Check the backend is running
  (`./scripts/dev.sh` output) and look for `GET /api/sessions/.../iterations/...`
  errors in the browser Network tab. The pane should show an explicit
  **"Couldn't load this run's detail"** + **Retry** instead of staying blank —
  if it stays blank, that is a bug.
- **Metrics row shows all zeros (`+0.00% · 0 trades · …`) for a real run:** the
  lightweight open response is missing meta fields — report this.
- **A 💡 insights box appears just from opening a session (no run clicked):**
  that is a regression — auto-insights-on-open is intentionally removed this
  phase.
- **No 💡 box / no OOS-aware suggestion in step 8:** verify `OPENAI_API_KEY` is
  set in the backend env and that walk-forward (step 7) completed before the
  regenerate.
