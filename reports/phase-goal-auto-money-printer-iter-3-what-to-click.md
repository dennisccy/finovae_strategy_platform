# Phase goal-auto-money-printer-iter-3 — What to Click (Operator Verification Guide)

**Phase:** goal-auto-money-printer-iter-3
**Time required:** ~5 minutes
**Written by:** ui-test-designer

---

## Prerequisites

- Frontend running at `http://localhost:3691`
- Backend running at `http://localhost:8691` with `OPENAI_API_KEY` set
  (quick check: `curl http://localhost:8691/api/health` → `200`)
- A terminal available to run two `curl` commands (open-universe runs have **no
  UI button** — they are started by API, by design)

---

## Verification Steps

<!-- Open-universe is API-triggered; the RESULTS are fully visible in the existing UI. -->

1. In a terminal, start **two** headless runs back-to-back:

   ```
   # Run A — explores ≥2 configs (J-12)
   curl -s -w "\nHTTP:%{http_code}\n" -X POST "http://localhost:8691/api/auto-sessions" \
     -H 'Content-Type: application/json' \
     -d '{"natural_language":"momentum breakout","objective":"robust","budget":{"max_iterations":2,"max_configs":2}}'

   # Run B — tiny token/USD budget, hits the hard cap (J-13)
   curl -s -w "\nHTTP:%{http_code}\n" -X POST "http://localhost:8691/api/auto-sessions" \
     -H 'Content-Type: application/json' \
     -d '{"natural_language":"budget probe","objective":"robust","budget":{"max_ai_tokens":1,"max_usd":0.0001,"max_configs":2,"max_iterations":2}}'
   ```
   - **Expect:** each command prints `HTTP:200` and a JSON body with a
     non-empty `"sessionId"` and `"status":"running"` (or `"queued"`).

2. Open `http://localhost:3691`, click the **"Sessions"** button (top of the
   page, clock icon), then under **"Live Sessions"** click the row
   **`Auto: momentum breakout`**.
   - **Expect:** the session opens; a **blue** status strip appears below the
     dark config bar reading `Automated run · iteration <N>/<M>` with a
     spinning icon.

3. Watch the left iteration list fill in for up to ~2 minutes (do **not**
   reload — it auto-updates). Read each iteration card's config line
   (`<symbol> · <timeframe> · <dates> · $<capital>`).
   - **Expect:** **≥2 iteration cards**, and at least two have a **different
     symbol and/or timeframe** (e.g. `BTCUSDT · 1h · …` and `ETHUSDT · 4h · …`)
     — not the same config repeated.

4. Look at the **far right end of the blue/colored strip** while it runs, then
   wait ~6 seconds and look again.
   - **Expect:** a dimmed right-aligned readout like `1,240 tok · $0.0021 · 1 cfg`
     that **increases** over time (tokens / `cfg` go up). Hover it → tooltip
     `AI tokens / USD / configs spent under the hard budget`. **No** `NaN`,
     `$undefined`, or blank.

5. Wait until the strip stops spinning (terminal). Scan the iteration cards.
   - **Expect:** exactly **one** card shows a small amber **`Best`** badge with
     a filled star (tooltip `Best iteration — selected by the robust
     walk-forward objective`); the strip turned terminal **without** any manual
     reload.

6. Click **"Sessions"** → click **`Auto: budget probe`**. Wait for it to reach
   a terminal state.
   - **Expect:** the strip is **amber** (not green, not red) with a
     **dollar-sign-in-a-circle** icon and the exact text
     `Automated run complete · budget reached · <N>/<M> iterations`; the
     right-end spend readout shows a final figure within the tiny cap; **no new
     iteration card** appears after it turns amber.

7. With `Auto: budget probe` still open, note the exact spend text at the right
   of the amber strip, then **hard-reload the browser (F5)**, click
   **"Sessions"**, and re-open **`Auto: budget probe`**.
   - **Expect:** still **amber** with the same `… budget reached …` text and
     the **same** spend numbers as before the reload (durable — survived the
     reload, not browser memory).

8. Click **"Sessions"** → click **"+ New Session"** at the top of the dropdown.
   - **Expect:** the new (manual) session shows **no status strip at all**
     below the config bar, and nowhere on screen do the words `NaN`,
     `undefined`, or `$undefined` appear — old/manual sessions degrade
     gracefully (additive-only change).

---

## What "Working Correctly" Looks Like

- One API call with **only** an objective + budget (no symbol/timeframe) starts
  a run that shows up in the existing **Sessions** list as `Auto: momentum
  breakout` and explores **≥2 different market configs** as normal iteration
  cards, with **one** marked by the amber **`Best`** star.
- The status strip shows a live, increasing `… tok · $… · … cfg` spend readout,
  and a budget-capped run ends in a distinct **amber** `budget reached` state
  that **survives a page reload**.
- A fresh manual session shows **no** strip and **no** `NaN`/`undefined` — the
  change is purely additive.

## Common Issues

- **`curl` returns `HTTP:422`:** check the JSON body — only `objective:"robust"`
  is supported, and **both** `symbol` and `timeframe` must be omitted for an
  open-universe run. `HTTP:500` is a real defect (should never happen).
- **No `Auto: …` row in the Sessions dropdown:** the POST did not return 200,
  or the backend is on a different port — re-check
  `curl http://localhost:8691/api/health`.
- **Strip stays blue "running" forever / never shows spend:** confirm
  `OPENAI_API_KEY` is set on the backend; an open-universe run needs LLM calls
  to make progress and to record token/USD spend.
- **Strip shows green `robust targets met` instead of amber for Run B:** the
  budget caps were not tight enough to force exhaustion — re-run the Run B
  `curl` exactly as written (`max_ai_tokens:1`, `max_usd:0.0001`).
- **Blank page / red error overlay:** the frontend isn't running or can't reach
  the backend — restart with `./scripts/dev.sh` from the repo root.
