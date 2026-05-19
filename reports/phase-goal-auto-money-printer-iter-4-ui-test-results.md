# Phase goal-auto-money-printer-iter-4 — UI Test Results

**Phase:** goal-auto-money-printer-iter-4
**Date:** 2026-05-19
**Written by:** browser-qa-agent

---

**Browser QA Verdict:** PASS

<!-- PASS: All P1 smoke + happy-path tests passed; regression J-02/J-08 re-verified
     live; pinned J-07–J-11 unchanged + carried B1 guard holds; no anti-goal. -->

**Overall:** 10/10 tests passed (0 skipped)

> **Test-plan provenance note (important for the evaluator/auditor):**
> `reports/phase-goal-auto-money-printer-iter-4-ui-test-plan.md` and
> `…-what-to-click.md` are **STUBs** (ui-test-design-phase.sh exited 1 without
> producing them). They were NOT trusted as input. Test cases below were
> derived directly from the **phase spec TESTING REQUIREMENTS**, the
> **ui-surface-map** "What to Test" column, and **user-visible-changes** —
> all authored artifacts. Every result is grounded in a **real live LLM run**
> (OpenAI + Anthropic keys both confirmed working behaviourally) and verified
> through Chrome MCP with scoped DOM `eval` queries (the SPA mounts ~90 legacy
> sessions; all assertions are scoped to the visible/active session container,
> never `body.innerText`).

---

## Live runs exercised (real LLM, tiny budget, no mocks)

| Run | sessionId | Request | Terminal | SCREEN/PROMOTE | best |
|-----|-----------|---------|----------|----------------|------|
| #1 | `a3e41bbb…` | open-universe, default model | complete · budget-exhausted · 6/3 | 4 SCREEN (gpt-5.4-mini) / 2 PROMOTE (gpt-5.4-mini) | SOL promote (robust 0.897) — not higher-ret ETH |
| #2 | `2c711bb7…` | open-universe, `model:claude-haiku-4-5` | complete · budget-exhausted · 6/3 | 4 SCREEN (**gpt-5.4-mini**) / 2 PROMOTE (**claude-haiku-4-5**) | SOL promote (robust 0.897) |
| pinned | `01322305…` | pinned BTC/USDT 4h, 3 iters | complete · budget-exhausted · 3/3 | none (correct) | iter 1 (robust 2.822) |
| J08C | `bfbd2cfe…` | open-universe "Bollinger" | complete · budget-exhausted · 6/3 | 4 SCREEN / 2 PROMOTE | ETH promote (robust 1.695) |

Run #2 is the primary J-14 evidence session (it makes the cheap-vs-stronger
model split observable at the data layer). Three independent open-universe
runs produced an identical staged shape — deterministic, not a fluke.

---

## Results Table

| Test ID | Name | Type | Priority | Expected | Actual | Verdict | Evidence |
|---------|------|------|----------|----------|--------|---------|----------|
| UT-01 | J-14 staged Activity feed: ≥3 SCREEN + k PROMOTE (k<screened) | smoke | P1 | Activity panel shows ≥3 `SCREEN N done —` accordion groups + exactly k `PROMOTE done —` groups, k<screened | **4 SCREEN + 2 PROMOTE** groups (k=2<4), verified on 3 independent runs | PASS | `UT-01-staged-feed-collapsed.png` |
| UT-02 | SCREEN group internals (marker / callout / no insights) | happy-path | P1 | Expand SCREEN group → violet `SCREEN config N: SYM TF`, green `… in-sample Sharpe … (cheap screen — no walk-forward)`, **no** blue insights card | violet `SCREEN config 1: BTC/USDT 4h`; green callout exact; **0 blue insights cards** | PASS | `UT-02-screen-group-expanded.png` |
| UT-03 | PROMOTE group internals (marker / callout / insights present) | happy-path | P1 | Expand PROMOTE group → violet `PROMOTE config: SYM TF (top-k survivor; in-sample Sharpe …)`, green `… robust … walk-forward WFE …`, blue insights card present | violet `PROMOTE config: ETH/USDT 4h (top-2 survivor; in-sample Sharpe 1.49)`; green callout exact; **1 blue insights card** present | PASS | `UT-03-promote-group-expanded-insights.png` |
| UT-04 | SCREEN vs PROMOTE completion-summary distinction | happy-path | P1 | SCREEN summary contains `in-sample Sharpe` + `(cheap screen — no walk-forward)` and **not** `walk-forward WFE`; PROMOTE summary contains `robust ` + `walk-forward WFE ` | All 4 SCREEN summaries match (no `walk-forward WFE`); both PROMOTE summaries contain `robust X.XXX, walk-forward WFE Y.YY` | PASS | `UT-01-staged-feed-collapsed.png` |
| UT-05 | Robust-best badge + per-iteration walk-forward display | happy-path | P1 | Exactly one "Best" badge on a **PROMOTE** iteration (robust-selected, not higher-raw-return screened); promoted detail shows populated walk-forward; screened detail shows none | Exactly **1** Best badge on `SOL …` PROMOTE (−2.13%, robust 0.897) — **not** the +21.11% ETH; SOL-promote detail: `WFE 2.11 ✓` + WalkForwardPanel + "Re-run"; screened ETH detail: "Run Walk-Forward" btn, no WFE | PASS | `UT-05-promoted-best-walkforward-detail.png` |
| UT-06 | AutoRunBar terminal state + spend (cfg == #PROMOTE) | happy-path | P1 | Amber `Automated run complete · budget reached · i/max iterations` + spend `… tok · $… · N cfg` where N == #PROMOTE groups | `Automated run complete · budget reached · 6/3 iterations` (amber, CircleDollarSign tone) + `16,125 tok · $0.0268 · 2 cfg`; **2 cfg == 2 PROMOTE groups** | PASS | `UT-01-staged-feed-collapsed.png` |
| UT-07 | Stronger model only on promoted (model routing) | functional | P2 | Screened iterations use cheapest model; promoted use the stronger requested model | Data/artifact layer: run#2 SCREEN nodes `modelUsed=gpt-5.4-mini` (catalog-cheapest), PROMOTE nodes `modelUsed=claude-haiku-4-5` (requested stronger). **UI does not render `modelUsed`** (documented "Not Visible Yet") — verified via API artifacts, not pixels | PASS (data-layer; see note) | API cross-check (no UI surface) |
| UT-08 | Pinned path unchanged + carried B1 final-iter insights | regression | P1 | Pinned session: `Automated iteration i/max` + `Backtest complete —`, **no** SCREEN/PROMOTE, **no** `stage` key; **final** iteration group still has a blue insights card | All 3 groups: `Automated iteration i/3` + `Backtest complete —`; `hasSCREEN/PROMOTE=false` everywhere; `stage` key absent on nodes; **every** group incl. **final 3/3** has exactly 1 blue insights card | PASS | `UT-06-pinned-no-screen-promote.png`, `UT-07-pinned-final-iter-insights-B1.png` |
| UT-09 | J-08 live status not stale under session switching | regression | P1 | Switch away from a running session and back → AutoRunBar reflects current backend state, not a frozen stale value | Left J08C at `Automated run · iteration 6/3` (primary/running) → switched to pinned (bar correctly showed pinned's own `3/3` terminal) → J08C finished → switched back → bar shows **`complete · budget reached · 6/3`** (amber/terminal), `isStaleRunning=false` | PASS | `UT-08-j08-live-running-before-switch.png`, `UT-09-j08-switchback-not-stale.png` |
| UT-10 | J-02 prior-run trades table + analysis panel re-bind | regression | P1 | On a completed prior run, selecting a prior iteration re-populates trades table + analysis panel with **that** iteration's data (not blank, not stale) | Selected BTC iter → "BTC 4H Bollinger Reversion" / Trade History **(18 trades)** / 18 rows + equity + rating; back, selected ETH iter → re-bound to "ETH 4H Bollinger Mean Reversion" / Trade History **(19 trades)** / 19 rows. Count + title changed correctly; never blank/stale | PASS | `UT-10-j02-rebind-btc-detail.png`, `UT-10-j02-rebind-eth-detail.png` |

---

## Passed Tests

### UT-01 — J-14 staged Activity feed (≥3 SCREEN + k PROMOTE, k<screened)
**Verdict:** PASS
**Evidence:** `reports/qa/goal-auto-money-printer-iter-4-evidence/UT-01-staged-feed-collapsed.png`
- Scoped DOM query of the visible session's Activity panel returned exactly **6 accordion groups**: 4 whose collapsed header status begins `SCREEN N done — …` and 2 whose header begins `PROMOTE done — …` → k=2 < screened=4 (the spec invariant).
- Reproduced identically on 3 independent live runs (#1, #2, J08C) — deterministic bounded seed prefix (BTC/USDT 4h, ETH/USDT 4h, SOL/USDT 4h, BNB/USDT 1h), top-2 promoted.

### UT-02 — SCREEN group internals
**Verdict:** PASS
**Evidence:** `…/UT-02-screen-group-expanded.png`
- Expanded SCREEN group 1: violet auto-run marker reads exactly `SCREEN config 1: BTC/USDT 4h`; green complete callout reads `SCREEN 1 done — BTC/USDT 4h: in-sample Sharpe -1.97, return -17.90%, 16 trades (cheap screen — no walk-forward)`.
- **Zero** blue (`bg-blue-50`) insights cards inside any SCREEN group → insights budget is not spent on screened-only configs (anti-goal honoured, visibly).

### UT-03 — PROMOTE group internals
**Verdict:** PASS
**Evidence:** `…/UT-03-promote-group-expanded-insights.png`
- Expanded PROMOTE (ETH) group: violet marker `PROMOTE config: ETH/USDT 4h (top-2 survivor; in-sample Sharpe 1.49)`; green callout `PROMOTE done — ETH/USDT 4h: return 21.11%, 17 trades, robust -999.581, walk-forward WFE 0.23`; **1** blue insights card present with prose summary.
- Observation (not a defect): suggestion **chips = 0**. The insights activity entries carry no structured `detail` (the LLM returned prose-only insights this run). The renderer (`ActivityLogEntry.tsx`, unchanged this phase) renders chips only when `entry.detail` parses to a suggestion array — chip presence is data-driven, identical to the unchanged pinned/manual path. The J-14 acceptance ("insights spent only on promoted survivors") is about the **card** presence/absence, which is correct (present on PROMOTE, absent on SCREEN).

### UT-04 — SCREEN vs PROMOTE completion-summary distinction
**Verdict:** PASS
- All 4 SCREEN summaries contain `in-sample Sharpe` AND the literal `(cheap screen — no walk-forward)`, and **none** contains `walk-forward WFE`.
- Both PROMOTE summaries contain `robust <num>` AND `walk-forward WFE <num>` (`WFE 0.23`, `WFE 2.11`). The expensive walk-forward signal is demonstrably reserved for promoted survivors and visible to the operator without new UI.

### UT-05 — Robust-best badge + per-iteration walk-forward
**Verdict:** PASS
**Evidence:** `…/UT-05-promoted-best-walkforward-detail.png`
- Exactly **one** "Best" badge in the visible session, on `SOL 4H RSI Reversion` — a **PROMOTE** iteration with return **−2.13%** and robust 0.897.
- The higher raw-return candidate (`ETH …`, **+21.11%**, incl. the screened-only ETH) is **NOT** marked best (ETH promote robust −999.581, WFE 0.23 fails the gate). The robust-best invariant (J-09/J-16) holds in the UI: raw return does not win.
- Promoted-best detail view: `WFE 2.11 ✓` pill + populated WalkForwardPanel metrics + "Re-run" button (WF already run). Screened ETH detail view: "Run Walk-Forward" button, no WFE pill (no walk-forward result). Screened-vs-promoted is visibly distinguishable by walk-forward presence.

### UT-06 — AutoRunBar terminal + spend
**Verdict:** PASS
- Visible AutoRunBar: `Automated run complete · budget reached · 6/3 iterations`, amber tone (`bg-amber-50 border-amber-200 text-amber-700`, CircleDollarSign) — the budget-exhausted terminal styling.
- Spend readout `16,125 tok · $0.0268 · 2 cfg`. The `2 cfg` figure equals the number of PROMOTE groups (2), **not** screened+promoted (6) — confirming the documented staged `max_configs` semantics (a "config" = one expensive PROMOTE) is what surfaces to the operator. (Run #1: `… · 2 cfg`; pinned: `… · 3 cfg` = one per pinned iteration, correct unchanged pinned semantics.)

### UT-07 — Stronger model only on promoted (data-layer)
**Verdict:** PASS (data/artifact layer — see explicit caveat)
- Run #2 (`model:claude-haiku-4-5`) persisted iteration nodes: 4 SCREEN nodes `modelUsed=gpt-5.4-mini` (the catalog-resolved cheapest), 2 PROMOTE nodes `modelUsed=claude-haiku-4-5` (the stronger requested model). Run #1 (default model == cheapest) correctly shows the same model on both stages because the requested model *is* the cheapest — consistent, not contradictory.
- **Caveat (not a failure):** the frontend does **not** render `modelUsed` anywhere (verified by source grep of `apps/frontend/src` — only the chat-input model selector references "model"). This matches the `user-visible-changes` "Not Visible Yet" section ("the operator only sees its *effect*"). The phase spec's *browser-visible* J-14 acceptance is satisfied by the walk-forward distinction (UT-05, visible); the model split is correct and proven at the artifact layer, which is the only place it exists. No new UI was required by the spec.

### UT-08 — Pinned path unchanged + carried B1 final-iteration insights
**Verdict:** PASS
**Evidence:** `…/UT-06-pinned-no-screen-promote.png`, `…/UT-07-pinned-final-iter-insights-B1.png`
- Pinned session (`01322305…`, BTC/USDT 4h, 3 iters): all 3 accordion groups show marker `Automated iteration i/3` and summary `Backtest complete — return …, … trades, robust …`. No `SCREEN`/`PROMOTE` text anywhere (per-group `hasSCREEN=false`, `hasPROMOTE=false`); persisted nodes carry **no** `stage` key.
- **Carried iter-3 B1 guard (the load-bearing carried fix):** every pinned iteration group — **including the final iteration 3/3** — contains exactly **1** blue insights card. The final pinned iteration's insights/prompt-refinement is **NOT** suppressed by the `max-configs` sentinel. Backend cross-check: the activity feed has 3 distinct `insights` entries (iters 1, 2, 3). This is exactly the regression the iter-3 lesson warned about; it does not reproduce.

### UT-09 — J-08 live status not stale under switching (re-verified LIVE)
**Verdict:** PASS
**Evidence:** `…/UT-08-j08-live-running-before-switch.png`, `…/UT-09-j08-switchback-not-stale.png`
- Pre-switch: J08C active, AutoRunBar `Automated run · iteration 6/3` (primary tone = live running).
- In-app switched (SessionPicker) to the unique pinned session → bar correctly re-bound to the pinned session's **own** terminal `… 3/3 iterations` (amber) — no cross-session staleness/contamination.
- J08C reached terminal in the background while not viewed. Switched back in-app → AutoRunBar now shows `Automated run complete · budget reached · 6/3 iterations` (amber/terminal) — the CURRENT backend state, **not** the frozen pre-switch `iteration 6/3 running`. `isStaleRunning=false`, `isCurrentTerminal=true`. The live poll re-armed on re-activation (iter-1/iter-2 lesson holds). The Activity panel still showed the full 4 SCREEN + 2 PROMOTE groups.

### UT-10 — J-02 prior-run trades table + analysis panel re-bind (re-verified LIVE)
**Verdict:** PASS
**Evidence:** `…/UT-10-j02-rebind-btc-detail.png`, `…/UT-10-j02-rebind-eth-detail.png`
- Completed prior-run session (J08C). Selected prior iteration A (BTC 4H Bollinger Reversion): detail panel populated — title "BTC 4H Bollinger Reversion", Equity Curve, Strategy Rating, **Trade History (18 trades)** with **18** table rows (not blank).
- Returned to the list, selected a different prior iteration B (ETH 4H Bollinger Mean Reversion): the trades table + right analysis panel **re-bound** — title "ETH 4H Bollinger Mean Reversion", **Trade History (19 trades)** with **19** rows, equity + rating refreshed. The data changed to B's (18→19 trades, BTC→ETH) — not stale from A, not blank. Independently corroborated earlier on run #2 (screened ETH 17 trades vs SOL-promote 26 trades + populated WF panel).

---

## Failed Tests

None.

---

## Skipped Tests

None. (Frontend `http://localhost:3691` up; backend `http://localhost:8691` up; Chrome MCP available; live LLM path confirmed working for both OpenAI `gpt-5.4-mini` and Anthropic `claude-haiku-4-5`.)

---

## Anti-goal / safety spot-checks (passed)

- **No secrets in artifacts:** scanned all four live session artifacts (runs #1, #2, J08C, pinned) for `sk-…`, `sk-ant-…`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `Bearer …` → **none found**. SCREEN/PROMOTE activity entries contain only symbol/timeframe/metrics text.
- **Pinned byte-unchanged:** no `stage` key on pinned nodes; activity strings identical to the legacy pinned path; B1 gate is a no-op on a normal pinned run (final-iteration insights still produced).
- **Staged `max_configs` semantics:** the operator-visible `… cfg` counter increments per **promoted** config only (open-universe = 2; pinned = one per iteration) — matches the documented staged definition; budget-exhausted terminal reached within the tiny budget on every run.

## Observations (non-blocking, for the evaluator/auditor)

1. **ui-test-plan / what-to-click artifacts are STUBs** (upstream `ui-test-design-phase.sh` exited 1). Tests were reconstructed from authored spec/surface-map/user-visible-changes; the top headline here is from a clean first-pass live run (no QA-FAIL→fix→reconcile cycle), so the iter-1 "reconciled-headline caution" does not apply — but the source-diff/artifact cross-checks were still performed (B1 activity-entry count, model split in persisted nodes, no-secrets scan).
2. **Suggestion chips = 0** inside PROMOTE insights cards: data-driven (LLM returned prose-only insights with empty `detail`), renderer unchanged & behaving correctly; not a J-14 regression. The insights *card* presence/absence (the actual acceptance) is correct.
3. **`modelUsed` is not a UI surface** (documented "Not Visible Yet"). Model routing is correct and verified at the persisted-artifact layer; the browser-visible staged signal is the SCREEN/PROMOTE text + the walk-forward presence/absence (both verified visible).

---

## Environment

- **Frontend URL:** http://localhost:3691
- **Backend URL:** http://localhost:8691 (live LLM: OpenAI `gpt-5.4-mini` + Anthropic `claude-haiku-4-5`, both confirmed working behaviourally)
- **Browser:** Chrome via `mcp__plugin_superpowers-chrome_chrome__use_browser` (scoped DOM `eval`, visible-container-only)
- **Test Date:** 2026-05-19
- **Evidence directory:** `reports/qa/goal-auto-money-printer-iter-4-evidence/`
