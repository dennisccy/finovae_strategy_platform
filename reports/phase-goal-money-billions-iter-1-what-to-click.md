# Phase goal-money-billions-iter-1 — What to Click (Operator Verification Guide)

**Phase:** goal-money-billions-iter-1
**Time required:** ~5 minutes
**Written by:** ui-test-designer

---

> This iteration changed **only the storage layer** (single-file Parquet OHLCV
> cache + durable-by-default session store). The UI looks identical. You are
> verifying that the existing journeys did **not regress** and that two new
> behaviors hold: a repeated identical run still works (and is faster), and run
> history survives a page reload. The single deepest check (survives a backend
> restart) is the optional last step.

---

## Prerequisites

- Frontend running at `http://localhost:3691`, backend running and reachable
- Backend has an OpenAI key configured (strategy generation + AI insights need it)
- No login required
- Symbol must be typed in `BASE/USDT` form — use **`BTC/USDT`** (with the slash)

---

## Verification Steps

1. Open `http://localhost:3691` in your browser
   - **Expect:** Header reads **"Finovae Strategy Platform"**; a config bar with
     Symbol / Timeframe / Start / End / Capital is visible; right panel shows
     **"No Iterations Yet"** (or an existing "Iterations (N)" list). No blank or
     error screen.

2. In the config bar set: **Symbol** = `BTC/USDT`, **Timeframe** = click `1h`,
   **Start** = `2023-01-01`, **End** = `2023-06-01`, **Capital** = `1500`
   - **Expect:** The Symbol field shows `BTC/USDT` with **no** red error; the
     `1h` timeframe button is highlighted/filled.

3. Click the **"Describe a trading strategy…"** box, type
   `Buy when RSI crosses below 30, sell when RSI crosses above 70`, then press
   **Enter** (or click the paper-plane send icon to the right of the box)
   - **Expect:** A card appears in the right "Iterations" panel and moves
     "Generating" → "Executing" → **"Complete"** (10–90s on a cold fetch). A
     green completion banner appears in the left panel. No red "Error" card.

4. Click the completed iteration card in the right panel
   - **Expect:** A detail view opens with a **"Backtest parameters"** box
     (`BTC/USDT`, `1h`, `2023-01-01 – 2023-06-01`, `$1,500`), a drawn
     **"Equity Curve"** chart, and a **"Trade History (N trades)"** table with
     at least one row. Note the **Total Return %** and **Total Trades** numbers.

5. Click the back arrow (top-left), then on the latest iteration card click
   **"Rerun"** (circular-arrow icon / "Rerun")
   - **Expect:** A second iteration runs to **"Complete"**; the panel header now
     reads **"Iterations (2)"**. This is the warm-cache re-run.

6. Open the second completed iteration and compare its **Total Return %** and
   **Total Trades** to the numbers you noted in step 4
   - **Expect:** They are **identical** (same numbers, same trade count), and the
     second run completed at least as fast as the first.
   - **Broken looks like:** different metrics for the same strategy/symbol/range,
     or the second run is dramatically slower than the first.

7. Press **F5** to reload the page (do not clear browser storage); wait for the
   "Sessions" button spinner to stop
   - **Expect:** The right panel still shows **"Iterations (2)"** for the same
     session — history persisted (durable store working). Not "No Iterations Yet".

8. Click an older (compact) iteration card in the history list
   - **Expect:** Its full detail reloads — parameters, metrics, Equity Curve, and
     Trade History — not blank, no "not found".

9. In that detail view, expand **"Walk-Forward Analysis"**, leave IS=6 / OOS=3,
   and click **"Run Walk-Forward"** (or "Re-run"); wait for it to finish
   - **Expect:** A **WFE** badge (`WFE x.xx ✓ / ~ / ✗`), an OOS metrics row, a
     per-window table with ≥1 row, and a **"Combined OOS Equity Curve"** chart.
     Not "No windows completed."

10. Look at the **left** activity panel for the blue lightbulb **AI insights**
    box under the completed run
    - **Expect:** Insight text plus **at least one** clickable blue suggestion
      pill. The box is not empty and shows no error.

> **Optional deep check (durability, ~1 extra min):** stop the backend and
> restart it **with `BACKTEST_STORE_DIR` unset** (no `.env` override of it),
> then reload `http://localhost:3691`. The same session and its "Iterations (2)"
> must still be there and openable. If history vanished, the durable-default
> store regressed.

---

## What "Working Correctly" Looks Like

- Steps 3–4: a real result — non-empty metrics, a drawn equity curve, a
  populated trade table — and a new card in the "Iterations" history
- Step 6: the warm re-run's metrics are **byte-identical** to the first run's
- Steps 7–8: history is still there after a refresh and prior runs reopen fully
- Steps 9–10: walk-forward and AI insights still render (no regression)

## Common Issues

- **Blank page / no model list / "Sessions" stuck spinning:** backend not
  running or not reachable — confirm the backend process is up and the frontend
  proxy points at it.
- **Red "Invalid symbol" in the left panel:** the Symbol must be `BTC/USDT`
  (with the slash), not `BTCUSDT`.
- **First run very slow:** expected on a genuine cold range — it is fetching
  from Binance once. The *second* (Rerun) should be faster; that is the point
  of this iteration.
- **History empty after F5 or after a backend restart:** this is the key
  regression signal for this iteration — the durable session store is not
  resolving to a persistent location. Flag it.
- **Different metrics on the Rerun:** determinism/cache regression — flag it
  (the deterministic proof is the pytest functional tests TC-01/TC-02).
