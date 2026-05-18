# goal-money-billions-iter-2 Frontend Handoff

**Phase:** goal-money-billions-iter-2
**Date:** 2026-05-18
**Agent:** developer
**Status:** complete

## What Was Built (UI)

The top parameter bar's **Symbol** and **Timeframe** controls are now
data-driven from the backend instead of hardcoded frontend literals (J-05).

### Symbol control
- **Before:** bare free-text `<input>` with regex validation, no suggestions.
- **After:** native combobox — same `<input>` (validation/uppercase/inline
  error unchanged) with `list="symbol-options"` + a `<datalist>` populated
  from `GET /api/symbols` (26 `BASE/USDT` pairs). User can pick a server
  symbol from the suggestion list **or** still type an arbitrary `BASE/USDT`
  pair (existing capability preserved — combobox, not a closed dropdown).

### Timeframe control
- **Before:** hardcoded button row `1m 5m 15m 1h 4h 1D`.
- **After:** a `<select>` whose options come from `GET /api/timeframes`.
  Option text is the server's human-readable label
  (`1 Minute / 5 Minutes / 15 Minutes / 1 Hour / 4 Hours / 1 Day`);
  the selected `value` (`1m`…`1d`) is what drives the backtest, unchanged.
  Styled identically to the existing Exchange `<select>` next to it — same
  Tailwind classes, no new visual style or effect introduced.

## Files Changed

- `apps/frontend/src/components/BacktestConfigBar.tsx` — only UI file changed
  (matches spec "UI surface changes: BacktestConfigBar.tsx only").

## How to Verify in the Browser (for browser-qa-agent)

Backend reference payloads to assert against (already confirmed healthy):
- `GET /api/symbols` → `{"symbols":["BTC/USDT","ETH/USDT",...,"PEPE/USDT"]}`
  (26 strings; first = `BTC/USDT`, last = `PEPE/USDT`).
- `GET /api/timeframes` → `{"timeframes":[{"value":"1m","label":"1 Minute"},
  {"value":"5m","label":"5 Minutes"},{"value":"15m","label":"15 Minutes"},
  {"value":"1h","label":"1 Hour"},{"value":"4h","label":"4 Hours"},
  {"value":"1d","label":"1 Day"}]}` (6 objects).

**J-05** — open the app:
- Timeframe: it is now a `<select>`. Its options must be exactly the 6 server
  labels above (not a button row). Capture an evidence screenshot of the open
  `<select>`.
- Symbol: focus the Symbol input; the `<datalist>` suggestions must list the
  26 server symbols (open the dropdown / start typing e.g. `BTC` → `BTC/USDT`
  suggested). The old set was never endpoint-backed; now it is.

**J-01** — submit a backtest:
- Type the strategy NL, ensure Symbol = `BTC/USDT` (type it or pick from the
  list), Timeframe `<select>` = `1 Hour`, set a date range, submit.
- Assert non-empty metrics, equity curve, trades table, and a new `run_id` in
  history.

**J-06** — repeat the identical symbol/timeframe/date-range run; assert it
completes, renders results, and appears in history (warm-cache path).

**J-02 / J-03 / J-04** — smoke only: open a prior run; run walk-forward;
request insights — confirm no regression from the control change.

**Error/fallback path** — if `/api/timeframes` is blocked/non-200 the Timeframe
`<select>` still shows the 6 standard options (built-in fallback) and a
backtest still runs; if `/api/symbols` is blocked the Symbol field is still a
working free-text input with the existing default. The bar must never be blank
or crash. (Confirmable from code: `.catch` + type-guard fallbacks; can be
exercised live by blocking the endpoints if desired.)

## UI States Handled

- **Loading / in-flight:** controls are immediately usable — Timeframe shows
  `FALLBACK_TIMEFRAMES`, Symbol is a working free-text input. No spinner is
  needed (and none was added, to avoid an out-of-scope layout change); the
  "sensible state while in flight" is a fully operational control set.
- **Success:** options are replaced by the live endpoint data.
- **Error (network / non-200 / malformed):** fallback retained; no crash.
- **Disabled:** every new control honors the existing `disabled` prop with the
  same `disabled:opacity-50 disabled:cursor-not-allowed` styling as siblings.

## Known Issues

- See the dev handoff: repo-level `npm run lint` fails on the untouched
  baseline because no ESLint config exists in the repo (pre-existing, out of
  scope). The changed file is lint-clean under standard react-ts rules.
- No visual redesign was performed (explicitly out of scope) — only the two
  controls changed their input mechanism; surrounding bar layout/style is
  untouched.
