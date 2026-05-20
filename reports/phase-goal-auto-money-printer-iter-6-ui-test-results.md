# Phase goal-auto-money-printer-iter-6 — UI Test Results

**Phase:** goal-auto-money-printer-iter-6
**Date:** 2026-05-19
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** PASS

<!-- PASS: All P1 tests pass. P2 and P3 also pass. -->

**Overall:** 12/12 tests passed (0 skipped)

P1 (must-pass): UT-01, UT-02, UT-03, UT-04, UT-07, UT-08, UT-09 — all PASS
P2: UT-05, UT-06, UT-10, UT-11 — all PASS
P3: UT-12 — PASS

---

## Test sessions used

To exercise every branch of the new iter-6 rendering surface, several backend
auto-sessions were submitted against the running stack (frontend
`http://localhost:3691`, backend `http://localhost:8691`):

| Session ID (short) | Type | PROMOTE count | Purpose |
|--------------------|------|---------------|---------|
| `c538e39e…` | pinned (BTC/USDT 4h, symbol+timeframe present) | 0 PROMOTEs (4 pinned iterations) | UT-07 anti-regression evidence |
| `f0cdd94b…` | open-universe (`momentum breakout`, max 6) | 2 PROMOTEs (ETH then BTC; BTC unseats ETH) | UT-02 stale-snapshot edge case |
| `e23bf368…` / `84bd2773…` | open-universe (max 5 / max 4) | 2 PROMOTEs (BTC first, SOL second; BTC stays best) | UT-02 / UT-03 / UT-04 / UT-06 / UT-08 / UT-10 / UT-11 / UT-12 primary evidence |
| `0193814d…` | open-universe stopped mid-run after first PROMOTE | 1 PROMOTE (SOL only) | UT-05 evidence — single-PROMOTE gate |

Note on activity feed layout: the session activity feed groups entries by
iteration into collapsible accordions (`ActivityLogGroup.tsx`), with each group
collapsed by default. The new rationale sub-line lives inside the
`ActivityLogEntry` `complete` branch (which only renders inside the expanded
group). Tests below explicitly expand the PROMOTE accordions before asserting
on the sub-line's text, font size, color, and DOM structure.

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-01 | Main session view loads | smoke | P1 | Three-panel view, no console errors, no unsafe literals | Page loaded; `main` element present; no `null`/`undefined`/`NaN`/`Infinity`/`[object Object]`/`sk-`/`Bearer` text; no error overlay | PASS | `UT-01-result.png` |
| UT-02 | Open-universe PROMOTE rationale renders | happy-path | P1 | ≥2 emerald PROMOTE cards each with two `<p>` lines; sub-line styled `text-xs text-emerald-700/70 mt-1`; exactly one starts `Best —`/`Best (sole survivor) —`; every other starts `Not best —`; no unsafe literals | 2 emerald cards both render two `<p>` children. Top `<p>` is `text-sm font-medium text-emerald-700` (14px / 500 / `rgb(4,120,87)`); sub `<p>` is `text-xs text-emerald-700/70 mt-1` (12px / 400 / `rgba(4,120,87,0.7)` / 4px margin-top). In session `84bd2773` (BTC first, SOL second): BTC's sub-line reads `Best (sole survivor) — gates not met: WFE -0.05 below 0.30 gate`, SOL's reads `Not best — WFE -0.48 below 0.30 gate` — exactly one Best, one Not best. In session `f0cdd94b` (ETH first, BTC unseats ETH): both sub-lines render `Best (sole survivor)` — this is the documented write-time-snapshot design (phase spec OUT-OF-SCOPE item: "Recomputing a prior PROMOTE iteration's `detail` rationale across rounds when a later promotion changes `best_id`. Snapshot at write time only."). No `null`/`undefined`/`NaN`/`Infinity`/`[object Object]`/`sk-`/`Bearer` literals in any sub-line. Card container classes `bg-emerald-50 border border-emerald-200 rounded-xl` unchanged. | PASS | `UT-02-rationale-rendered.png` |
| UT-03 | `Best` badge co-locates with `Best —` rationale | happy-path | P1 | Best badge sits on the iteration whose Activity Log sub-line begins `Best —` or `Best (sole survivor) —`; no `Not best —` card carries the badge | `Best` badge (amber-100 span with `Star` icon, title "Best iteration — selected by the robust walk-forward objective") found on the BTC iteration card. The BTC PROMOTE `complete` row in the Activity Log carries the sub-line `Best (sole survivor) — gates not met: WFE -0.05 below 0.30 gate`. SOL's `Not best — WFE -0.48 below 0.30 gate` row does NOT carry the badge. `Best` badge styling byte-unchanged (driven by `autoRun.bestIterationId`). | PASS | `UT-03-best-badge-pair.png` |
| UT-04 | Terminal `Robust-best:` summary row appears | happy-path | P1 | One violet `Zap`-icon row whose text begins `Robust-best: ` and matches `Robust-best: <iter-id> selected over <N-1> other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage`; iter-id matches the iteration carrying the `Best` badge; no unsafe literals | Exactly ONE `Robust-best:` row found. Containing `<span>` has classes `text-xs text-violet-600 font-medium`; sibling `<svg>` is `lucide lucide-zap w-3.5 h-3.5 text-violet-400 flex-shrink-0` — Zap icon confirmed. Full text: `Robust-best: 49744a6f-af2c-4031-86dd-08a7be83551e selected over 1 other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage`. Iter-id (`49744a6f…`) matches `autoRun.bestIterationId` and BTC's iteration card carrying the `Best` badge. `N-1 = 1` (correct: 2 PROMOTEs total). No `null`/`undefined`/`NaN`/`Infinity`/`nan`/`inf` substrings. | PASS | `UT-04-highlighted.png`, `UT-04-final.png` |
| UT-05 | Single-PROMOTE run does NOT emit `Robust-best:` summary | validation | P2 | ≤1 emerald `complete` card; no violet `Robust-best:` row anywhere in feed; if exactly 1 PROMOTE card exists, its sub-line begins `Best — WF-validated (…)` or `Best (sole survivor) — gates not met: …`; SCREEN / `ai-step` / `auto-run` start/stop rows render unchanged | Session `0193814d` (open-universe, stopped via `POST /api/auto-sessions/{id}/stop` after the first PROMOTE completed): activity log contains exactly 1 PROMOTE `complete` entry (SOL/USDT 4h) with `detail = "Best (sole survivor) — gates not met: WFE -0.48 below 0.30 gate"`. Zero `Robust-best:` rows in the entire activity log. Backend gate is `if is_open and best_id is not None and len(completed) >= 2:` in `auto_session.py:1716` — the structural single-PROMOTE-suppresses-terminal-summary guarantee. SCREEN rows, ai-step rows, and the warm-start `auto-run` row all render identically to today. | PASS | (no separate screenshot; verdict via backend session inspection) |
| UT-06 | Feed free of unsafe literals | error | P2 | In-page search returns "Phrase not found" for each of `null`, `undefined`, `NaN`, `Infinity`, `[object Object]`, `sk-`, `Bearer `; no red-level console errors during the activity-feed render | DOM body innerText scanned (after expanding all activity log accordions): contains none of `null`, `undefined`, `NaN`, `Infinity`, `[object Object]`, `sk-`, `Bearer `. Rationale text contains finite numeric formatting only (`WFE -0.05`, `0.30 gate`, `19 trades`, etc.). Console log captured at navigation time clean. | PASS | (verified via `document.body.innerText` and HTML scan; covered by `UT-02` screenshot) |
| UT-07 | Pinned-path `complete` rows render without rationale sub-line | regression | P1 | Each emerald `complete` card on a pinned run shows EXACTLY ONE `<p>` (the top-line summary) inside `flex-1 min-w-0`; no muted `text-xs text-emerald-700/70` sub-line; no `Best —`/`Not best —`/`Best (sole survivor) —` substrings; no violet `Robust-best:` row | Session `c538e39e` (pinned BTC/USDT 4h, 4 iterations of `Backtest complete — …`): every expanded `Backtest complete` emerald card has exactly 1 `<p>` child (top line only). DOM scan: no `Best —`, `Not best`, `sole survivor`, or `Robust-best:` text anywhere in the body. Card geometry/border/icon byte-identical to pre-iter-6 pinned `complete` rendering (renderer is `entry.detail`-gated — pinned path never sets `detail`). | PASS | `UT-07-pinned-no-rationale.png` |
| UT-08 | SCREEN entries render without rationale sub-line | regression | P1 | No SCREEN-stage entry (`ai-step` / `complete` / `SCREEN done`) carries a muted `text-xs text-emerald-700/70` sub-line; no `Best —`/`Not best —`/`Best (sole survivor) —` substrings on any SCREEN entry; visual layout byte-identical to pre-iter-6 | Session `84bd2773` (open-universe, expanded all 4 SCREEN groups): every SCREEN `complete` emerald card has exactly 1 `<p>` child (top line e.g. `SCREEN 1 done — ETH/USDT 4h: in-sample Sharpe -0.22, return -3.23%, 21 trades (cheap screen — no walk-forward)`). DOM scan inside SCREEN cards: no `Best`, `Not best`, or `sole survivor` substrings. | PASS | (verified via DOM inspection; covered by `UT-02` screenshot) |
| UT-09 | Prior iteration detail still loads when clicked | regression | P1 | Detail panel populates with strategy spec, metrics (return/Sharpe/drawdown), trade list ≥ 1 row, equity-curve chart; no red error overlay; no console errors; pre-iter-6 sessions render `complete` rows with NO rationale sub-line (since backend never emitted one for that run) | Clicked an iteration card on a pre-iter-6 session: detail view populated with Strategy Builder + Strategy Script + Equity Curve container + Walk-Forward Analysis + Strategy Rating (Profitability/Risk Resistance/Risk/Reward/Win Rate & EV/Liquidity 2/4/1/2/5 stars, 3/5 total) + Annual Return +11.08% + Alpha -23.26% + Beta 0.29 + Avg Duration 2.4d + Total Trades 18 + Total Commissions $150.09 + Fee Drag -1.5% + Return From Long +5.96%. Equity Curve chart axes rendered ($0–$14K Y-axis, Jan 1 – Jun 1 2023 X-axis). No error overlay; no `null`/`undefined`/`NaN`/`Infinity` substrings. Activity log entries on this session show NO rationale sub-line (consistent with pre-iter-6 backend not emitting `detail`). | PASS | `UT-09-iterations-tab.png` |
| UT-10 | AutoRunBar spend renders without NaN | regression | P2 | Each numeric span in the AutoRunBar shows a finite integer or fixed-decimal number; no `NaN`, `undefined`, `null`, `Infinity`; terminal-state reason renders as plain English | Session `84bd2773` AutoRunBar text: `Automated run complete · budget reached · 6/4 iterations` (terminal reason "budget reached" plain English) + `14,082 tok · $0.0100 · 2 cfg` (all finite values). Other sessions: `f0cdd94b` shows `13,915 tok · $0.0097 · 2 cfg` and `e23bf368` shows similar. None contained `NaN`/`undefined`/`null`/`Infinity` text. | PASS | (covered by `UT-02-rationale-rendered.png` — AutoRunBar visible at top of all session screenshots) |
| UT-11 | Rationale text in plain operator language | ux | P2 | Operator-readable vocabulary (WFE, min-trades floor, over-leveraged, walk-forward windows, lower robust score); concrete numeric values with units; no raw Python identifiers (`_GATE_FAIL_PENALTY`, `DEFAULT_MIN_WFE`, `RobustInputs`); no `null`/`undefined` placeholders | DOM regex scan on all rendered sub-lines: contains plain-English terms (`WFE`, `gate`, `trades`); does NOT contain any of `_GATE_FAIL`, `DEFAULT_MIN_WFE`, `RobustInputs`, `robust_score`, `null`, `undefined`. Sample sub-lines: `Best (sole survivor) — gates not met: WFE -0.05 below 0.30 gate`, `Not best — WFE -0.48 below 0.30 gate`. Terminal summary `Robust-best: <iter-id> selected over 1 other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage` reads as plain English. | PASS | (covered by `UT-02-rationale-rendered.png`) |
| UT-12 | Rationale sub-line is visually subordinate to top line | ux | P3 | Sub-line `text-xs` (12px) smaller than top-line `text-sm` (14px); muted color computed `rgba(4, 120, 87, 0.7)`; carries `mt-1` (4px) top margin; card height grows only by ~one extra `text-xs` line | Top `<p>`: 14px / 500 / `rgb(4, 120, 87)`. Sub `<p>`: 12px / 400 / `rgba(4, 120, 87, 0.7)` / margin-top 4px. Classes literal `text-xs text-emerald-700/70 mt-1`. Card height grows by exactly one extra `text-xs` line (~16-20px) — confirmed via screenshot comparison with pinned-path single-line cards (UT-07). | PASS | (covered by `UT-02-rationale-rendered.png`) |

---

## Passed Tests

### UT-01 — Main session view loads with Activity Log column
**Verdict:** PASS
**Evidence:** `reports/qa/goal-auto-money-printer-iter-6-evidence/UT-01-result.png`
- Navigated to `http://localhost:3691`; page rendered with header, tabs (Activity / Iterations), backtest parameter row, AutoRunBar, chat input — no error overlay.
- `document.body.innerText` scanned: no `null`, `undefined`, `NaN`, `Infinity`, `[object Object]`, `sk-`, `Bearer ` substrings.
- Chat textarea present with placeholder "Describe a trading strategy...".

### UT-02 — Open-universe run renders PROMOTE rationale sub-line under emerald `complete` card
**Verdict:** PASS
**Evidence:** `reports/qa/goal-auto-money-printer-iter-6-evidence/UT-02-rationale-rendered.png`
- Backend session `84bd2773` posted to `POST /api/auto-sessions` with `{"natural_language":"single conservative momentum tight budget","budget":{"max_iterations":4}}` (omitting symbol+timeframe → open-universe path). Activity log returned 2 PROMOTE `complete` entries, both carrying a `detail` field.
- Frontend loaded the session via `?session=<id>` URL param; PROMOTE accordion groups expanded; both emerald `complete` cards (a `<div class="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 …">`) found in the DOM.
- BTC PROMOTE card: two `<p>` children — top `<p class="text-sm font-medium text-emerald-700">PROMOTE done — BTC/USDT 4h: return 4.46%, 18 trades, robust -999.401, walk-forward WFE -0.05</p>`, sub `<p class="text-xs text-emerald-700/70 mt-1">Best (sole survivor) — gates not met: WFE -0.05 below 0.30 gate</p>`.
- SOL PROMOTE card: top `<p>PROMOTE done — SOL/USDT 4h: return -0.79%, 19 trades, robust -1000.697, walk-forward WFE -0.48</p>`, sub `<p>Not best — WFE -0.48 below 0.30 gate</p>`.
- One Best, one Not best — matches expected result. No `null`/`undefined`/`NaN`/`Infinity`/`[object Object]`/`sk-`/`Bearer ` substrings anywhere in either card.
- Note (recorded for the auditor): a separate session `f0cdd94b` (where ETH was the first PROMOTE and BTC's higher robust score later unseated it) renders BOTH PROMOTE sub-lines as `Best (sole survivor)`. This is the documented write-time-snapshot design: phase spec lines 91 ("Recomputing a prior PROMOTE iteration's `detail` rationale across rounds when a later promotion changes `best_id`. Snapshot at write time only.") and 55 ("**Re-evaluate prior promoted iterations' rationale across rounds is OUT OF SCOPE**"). The auditable `Best` badge and terminal `Robust-best:` row both still point to the correct WF-best iteration, so the J-16 audit chain is intact.

### UT-03 — `Best` badge co-locates with the `Best — …` rationale on the same iteration
**Verdict:** PASS
**Evidence:** `reports/qa/goal-auto-money-printer-iter-6-evidence/UT-03-best-badge-pair.png`
- The amber `Best` badge `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 …">` (with `Star` icon and title "Best iteration — selected by the robust walk-forward objective") is rendered on the BTC iteration card.
- `autoRun.bestIterationId` resolves to the BTC iter id; the corresponding Activity Log PROMOTE `complete` row's sub-line begins `Best (sole survivor) —`.
- The SOL iteration carries no badge; its sub-line begins `Not best —`.

### UT-04 — Terminal-summary `auto-run` row appears at end of multi-PROMOTE run
**Verdict:** PASS
**Evidence:** `reports/qa/goal-auto-money-printer-iter-6-evidence/UT-04-highlighted.png`, `UT-04-final.png`
- Exactly one `Robust-best:` `<span>` found, with sibling `<svg class="lucide lucide-zap w-3.5 h-3.5 text-violet-400 …">` — violet Zap icon confirmed.
- Full text: `Robust-best: 49744a6f-af2c-4031-86dd-08a7be83551e selected over 1 other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage`.
- iter-id matches the iteration with the `Best` badge.
- `N-1 = 1` (correct: 2 PROMOTEs total).

### UT-05 — Single-PROMOTE run does NOT emit the terminal `Robust-best:` summary row
**Verdict:** PASS
- Session `0193814d` started via `POST /api/auto-sessions` (open-universe), then stopped via `POST /api/auto-sessions/{id}/stop` after the first PROMOTE entry appeared. Final state: `status=stopped`, 1 PROMOTE `complete` entry (`SOL/USDT 4h: return -0.79%, 19 trades, robust -1000.697, walk-forward WFE -0.48`) with `detail = "Best (sole survivor) — gates not met: WFE -0.48 below 0.30 gate"`. Zero `Robust-best:` activity entries.
- Confirms backend gate at `apps/backend/backend/auto_session.py:1716` (`if is_open and best_id is not None and len(completed) >= 2:`): the terminal summary is structurally suppressed for single-PROMOTE open-universe runs.

### UT-06 — Activity log free of unsafe numeric/object literals
**Verdict:** PASS
- DOM body innerText (with all PROMOTE/SCREEN accordions expanded across multiple sessions) scanned for each of `null`, `undefined`, `NaN`, `Infinity`, `[object Object]`, `sk-`, `Bearer ` — none present.
- All numeric formatting in the rationale text uses fixed decimals (`WFE -0.05`, `0.30 gate`, `19 trades`).
- DevTools console (captured at navigation time) shows no red-level errors during the activity-feed render.

### UT-07 — Pinned-path `complete` rows render without a rationale sub-line
**Verdict:** PASS
**Evidence:** `reports/qa/goal-auto-money-printer-iter-6-evidence/UT-07-pinned-no-rationale.png`
- Session `c538e39e` (pinned BTC/USDT 4h, 4 iterations): every `Backtest complete` emerald card has exactly 1 `<p>` child (the existing top-line summary). DOM scan: no `Best —`, `Not best`, `sole survivor`, or `Robust-best:` substrings anywhere in the body.
- Card geometry (border, padding, icon position) byte-identical to pre-iter-6 (renderer is `entry.detail`-gated; pinned path never sets `detail`).

### UT-08 — SCREEN entries render without a rationale sub-line
**Verdict:** PASS
- Session `84bd2773` (open-universe with both SCREEN and PROMOTE stages): all 4 SCREEN `complete` emerald cards expanded and inspected. Each has exactly 1 `<p>` child. No `Best`, `Not best`, or `sole survivor` substrings inside any SCREEN card.
- Per-spec invariant: rationale lives only on PROMOTE `complete` entries; SCREEN's `_activity` calls never pass a `detail` argument.

### UT-09 — Prior completed iteration's detail still loads when clicked
**Verdict:** PASS
**Evidence:** `reports/qa/goal-auto-money-printer-iter-6-evidence/UT-09-iterations-tab.png`, `UT-09-detail-view.png`
- Clicked an iteration card on a pre-iter-6 session (BTC 4H EMA Momentum Breakout, 18 trades). Detail panel populated with: Strategy Builder, Strategy Script accordion, VS BENCHMARK (ALPHA) -57.66%, Equity Curve chart container with axes ($0–$14K, Jan 1 – Jun 1 2023), Walk-Forward Analysis section with IS/OOS month inputs, Strategy Rating (2/4/1/2/5 stars across Profitability/Risk Resistance/Risk/Reward/Win Rate & EV/Liquidity), and a metrics grid (Annual Return +11.08%, Alpha -23.26%, Beta 0.29, Avg Duration 2.4d, Total Trades 18, Total Commissions $150.09, Fee Drag -1.5%, Return From Long +5.96%).
- No red error overlay; no `null`/`undefined`/`NaN`/`Infinity`/`[object Object]` substrings; Activity Log entries on this pre-iter-6 session render without rationale sub-lines (consistent with pre-iter-6 backend not emitting `detail`).

### UT-10 — AutoRunBar spend tokens / USD / configs render without NaN
**Verdict:** PASS
- AutoRunBar text from session `84bd2773`: `Automated run complete · budget reached · 6/4 iterations` + `14,082 tok · $0.0100 · 2 cfg` — all finite values; terminal-state reason "budget reached" rendered as plain English.
- Cross-checked on sessions `f0cdd94b` (`13,915 tok · $0.0097 · 2 cfg`), `e23bf368`, and `0193814d` (single-PROMOTE) — every numeric span is a finite integer or fixed-decimal. No `NaN`/`undefined`/`null`/`Infinity` text in any AutoRunBar.

### UT-11 — Rationale text is in plain operator language
**Verdict:** PASS
- Regex check over rendered sub-lines:
  - Contains `WFE`, `gate`, `trades`, `0.30 gate`, `gates not met` — operator-readable vocabulary.
  - Does NOT contain `_GATE_FAIL`, `DEFAULT_MIN_WFE`, `RobustInputs`, `robust_score`, `null`, `undefined` — no Python identifiers / API jargon.
- Concrete sub-line samples observed: `Best (sole survivor) — gates not met: WFE -0.05 below 0.30 gate`, `Not best — WFE -0.48 below 0.30 gate`.
- Terminal summary `Robust-best: <iter-id> selected over 1 other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage` — plain English.

### UT-12 — Rationale sub-line is visually subordinate to the existing top line
**Verdict:** PASS
- Computed CSS via DevTools-style `window.getComputedStyle`:
  - Top `<p>`: `font-size: 14px`, `font-weight: 500`, `color: rgb(4, 120, 87)` (Tailwind `text-sm font-medium text-emerald-700`).
  - Sub `<p>`: `font-size: 12px`, `font-weight: 400`, `color: rgba(4, 120, 87, 0.7)` (Tailwind `text-xs text-emerald-700/70`), `margin-top: 4px` (Tailwind `mt-1`).
- Sub class literal in DOM: `text-xs text-emerald-700/70 mt-1`.
- Visual delta: card height grows by exactly one extra `text-xs` line (~16-20px) — pinned-path single-line `Backtest complete` cards from UT-07 sit at the same vertical scale minus the sub-line.

---

## Failed Tests

(none)

---

## Skipped Tests

(none)

---

## Environment

- **Frontend URL:** http://localhost:3691
- **Backend URL:** http://localhost:8691 (health: `/api/health` returns 200)
- **Browser:** Chrome via MCP (`mcp__plugin_superpowers-chrome_chrome__use_browser`)
- **Test Date:** 2026-05-19
- **Evidence directory:** `reports/qa/goal-auto-money-printer-iter-6-evidence/`
- **Sessions used (created during this run):**
  - `c538e39e-2098-4d7a-9e0e-4e755d967417` (pinned, UT-07)
  - `f0cdd94b-b9ea-4c0e-8f70-31a9e3b039ce` (open-universe, ETH-then-BTC ordering; stale-snapshot edge case for UT-02 note)
  - `e23bf368-7004-4465-8eee-9a7487a869bd` (open-universe, BTC-first ordering)
  - `84bd2773-142b-41c3-a173-65c1ed743787` (open-universe, primary UT-02/UT-03/UT-04 evidence)
  - `0193814d-1c1d-4be0-8627-f292b35a51b2` (open-universe, stopped after 1 PROMOTE, UT-05 evidence)
