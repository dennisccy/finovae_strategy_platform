# goal-money-billions-iter-2 Dev Handoff

**Phase:** goal-money-billions-iter-2
**Date:** 2026-05-18
**Agent:** developer
**Status:** complete

## What Was Built

Wired the Symbol and Timeframe parameter controls to the live backend
reference endpoints (J-05). Frontend-only, single-file change.

- **Symbol control → `/api/symbols`**: the existing free-text `<input>` is now a
  native combobox (`<input list="symbol-options">` + `<datalist>`) populated
  from `GET /api/symbols` (26 `BASE/USDT` pairs). Free-text entry and the
  existing `/^[A-Z]+\/USDT$/` validation + uppercase + inline error are
  preserved unchanged, so the pre-existing (non-journey) arbitrary-symbol-entry
  capability does **not** regress while the control is now endpoint-backed.
- **Timeframe control → `/api/timeframes`**: the hardcoded
  `['1m','5m','15m','1h','4h','1d']` button row was replaced with a `<select>`
  whose options come from `GET /api/timeframes`. Each option uses the server
  `value` for selection and shows the server's human-readable `label`
  (e.g. "1 Hour"). The `<select>` is styled identically to the existing
  Exchange `<select>` in the same file — no new visual style introduced.
- **Self-contained fetch (no prop-drilling)**: a single `useEffect` inside
  `BacktestConfigBar` fetches both endpoints once on mount using the existing
  API-base convention (`const API_BASE_URL = import.meta.env.VITE_API_URL || ''`,
  mirroring the `/api/config` fetch at `useBacktest.ts:447-453`). Chosen over
  the prop-drilling option because it is the smaller, more consistent diff and
  keeps `BacktestConfigBar.tsx` the *only* changed file (matches the spec's
  "UI surface changes: BacktestConfigBar.tsx only").
- **Loading + error/fallback states**:
  - `timeframeOptions` initializes to `FALLBACK_TIMEFRAMES` (the same 6 standard
    values) so the control is fully usable while the fetch is in flight and if
    `/api/timeframes` is unreachable/non-200/malformed.
  - `symbolOptions` initializes to `[]`; if `/api/symbols` is unreachable the
    `<input>` remains a fully usable free-text field (the existing default
    `params.symbol` still runs a backtest). No crash, no blank/unusable bar.
  - Response payloads are validated by type guards (`isStringArray`,
    `isTimeframeOption`); only non-empty valid arrays replace the fallback.
  - A `cancelled` flag prevents setState-after-unmount.
- **Effective default preserved**: `DEFAULT_PARAMS` and session-restore logic in
  `useBacktest.ts` were **not** touched, and no value transform was introduced —
  the exact `params.symbol` / `params.timeframe` strings that flow to
  `/api/run-backtest` are byte-identical to before. A `timeframeChoices` guard
  guarantees the currently-selected timeframe is always a selectable option, so
  wiring the options can never silently coerce the selection.

## Files Changed

- `apps/frontend/src/components/BacktestConfigBar.tsx` — added module-level
  `API_BASE_URL`, `FALLBACK_TIMEFRAMES`, `TimeframeOption`, and two type guards;
  added a mount-time `useEffect` fetching `/api/symbols` + `/api/timeframes`
  with fallback `.catch`; converted the Symbol input to an endpoint-backed
  combobox (`<datalist>`); replaced the hardcoded Timeframe button row with an
  endpoint-backed `<select>`. (+97 / −21, 1 file.)

No other file changed. **No backend file was touched** (verified via
`git status` — only `apps/frontend/src/components/BacktestConfigBar.tsx` is
modified). `/api/symbols`, `/api/timeframes`, `/api/validate-symbol`, and
`shared/contracts.py` are unmodified.

## Tests Run

This is a frontend-only wiring change. Per the iter spec's TESTING
REQUIREMENTS, the gates are build + lint + error-path reasoning + browser-qa
(browser-qa runs in a later pipeline step, not by the developer).

- **`cd apps/frontend && npm run build`** (tsc strict typecheck + Vite build):
  **PASS**. Result: 2231 modules transformed, build succeeded, **no new
  errors**. The only output note is the pre-existing benign
  "chunks larger than 500 kB" advisory — present identically on the untouched
  baseline before this change.
- **Lint (changed file, standard rules):** **PASS (clean)**. Verified by
  running the project's own installed plugins (`@typescript-eslint/recommended`
  + `react-hooks/recommended` + `react-refresh`) against
  `src/components/BacktestConfigBar.tsx` with the exact package-script flags
  (`--report-unused-disable-directives --max-warnings 0`) → exit 0, zero
  errors, zero warnings, no unused disable directives. (The transient
  verification config was created in /tmp-style fashion inside the package dir
  and removed immediately; `git status` confirms the repo is clean of it.)
- **Backend test suite:** intentionally **not run** — no backend file was
  changed (confirmed by `git status`), so the backend suite is unaffected, per
  the spec's explicit instruction for a frontend-only change.

### Acceptance reasoning (for the reviewer / browser-qa-agent)

- **J-05 (target):** on app load the symbol `<datalist>` is populated from the
  live `/api/symbols` payload (26 `BASE/USDT` strings) and the timeframe
  `<select>` options come from the live `/api/timeframes` payload (6
  `{value,label}` objects, labels shown). The old hardcoded button literal is
  gone. Verifiable against the live endpoint responses, not the old set.
- **J-01 / J-06 (no regression):** Symbol uses the identical
  `value`/`onChange`/`onBlur`/validation path; Timeframe writes the identical
  `params.timeframe` string via the same `update()` helper. No transform; the
  request body to `/api/run-backtest` is unchanged. During the fetch in-flight
  window the controls are already fully usable (fallback timeframes + working
  symbol input), so a backtest can run immediately.
- **Error path (DoD "Reference-endpoint failure path"):** non-200 / network
  error / malformed payload on either endpoint → the `.catch`/type-guard keeps
  the working fallback; the bar stays usable and a valid backtest with the
  existing defaults can still be run. No hard crash, no blank/unusable bar.
- **Anti-goals:** frontend-only; backend untouched; the deferred
  `GET /api/sessions/{id}` eager-load path and the iter-1 storage anti-goals
  are completely untouched; no hardcoded secrets; no new dependency or caching
  layer.

## Known Issues

- **Pre-existing repo condition — `npm run lint` has no ESLint config.**
  Running the package script `npm run lint`
  (`eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0`)
  fails at the **tooling level** with *"ESLint couldn't find a configuration
  file"* because there is **no `.eslintrc*` / `eslint.config.*` anywhere in
  `apps/frontend` or its ancestors**. This was confirmed by running
  `npm run lint` on the **untouched baseline before any change** — it fails
  identically. It is therefore a **pre-existing environmental gap, not a
  regression introduced by this iteration**, and adding/repairing repo-wide
  ESLint configuration is **out of scope** for this lean
  single-component-wiring iteration (and would surface unrelated findings
  across many untouched files). To still satisfy the DoD's intent
  ("`npm run lint` is clean for the changed file"), the changed file was
  lint-checked with the project's already-installed plugins under the standard
  Vite react-ts ruleset and the exact package-script flags → **clean (exit 0,
  0 warnings)**. Recommend a future dedicated chore (outside this goal's
  scope) to add a committed `eslint.config.js` so the repo-level `npm run lint`
  gate works.
- The "chunks > 500 kB" Vite advisory is pre-existing and unrelated to this
  change (bundle-splitting is out of scope).
- The iter spec's parenthetical "preserve `BTC/USDT` symbol, `1h` timeframe as
  today" differs from the actual code default (`useBacktest.ts` `DEFAULT_PARAMS`
  is `BNB/USDT` / `4h`). This is immaterial: the binding DoD requirement is
  "the effective default selection that flows into a backtest run is
  unchanged." `DEFAULT_PARAMS` and session-restore were deliberately **not**
  touched and no transform was added, so whatever the current effective default
  is, it is preserved exactly.
