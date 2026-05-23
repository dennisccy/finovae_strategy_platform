# QA Report — goal-financial_free-iter-4

**Verdict:** PASS

**Phase:** goal-financial_free-iter-4 — Staged SCREEN→PROMOTE cost-tiering for the open-universe search (J-14)
**Date:** 2026-05-23
**Agent:** qa (MODE 2 — QA validation)
**Frontend Present:** yes

---

## Summary

J-14 (staged SCREEN→PROMOTE cost-tiering) is verified end-to-end. The full hermetic backend suite is green except the single known pre-existing red (`test_directions_cache`, explicitly out-of-scope). A **live, real-LLM open-universe run** (the spec's recommended QA recipe) was triggered against the QA-managed backend and verified through the exact endpoint the UI polls (`GET /api/sessions/{id}`): a cheap SCREEN sweep over 3 seed configs on `gpt-5.4-mini` with no walk-forward, then a PROMOTE of the top-1 (k=1 < 3) to `claude-haiku-4-5` **with** walk-forward, best WFE-gated from promoted only. Live token/USD/configs counters incremented across polls (J-08) and the terminal `autoRun` state survives a re-fetch (J-10 durable persistence).

**Live browser pixel capture was NOT obtained** — the QA-managed frontend on `:3692` went down mid-window (no listener; FE 200 at run start → 000 from poll 3 onward). This is an environment/infra condition, not an application defect (the backend stayed `200` throughout). Per the qa.md rule ("Do NOT mark FAIL just because browser checks were skipped / frontend not running") and the spec's sanctioned fallback, the backend-endpoint substitute was executed in full **with** the live-service health-check recorded, and the FE render path was confirmed in code. See "Browser checks" for the honest health-check trail.

---

## Step 1 — Artifact verification

| Artifact | Status |
|----------|--------|
| `docs/handoffs/goal-financial_free-iter-4-dev.md` | ✅ present |
| `docs/handoffs/goal-financial_free-iter-4-frontend.md` | ✅ present |
| `reports/reviews/goal-financial_free-iter-4-review.md` | ✅ PASS_WITH_NOTES |
| `runs/goal-financial_free-iter-4/status.json` | ✅ present (review_passed) |
| `reports/qa/goal-financial_free-iter-4-test-plan.md` | ✅ present (executed below) |

---

## Step 2 — Backend tests

Command: `cd apps/backend && .venv/bin/python -m pytest -q`
Log: `reports/qa/goal-financial_free-iter-4-test.log`

```
1 failed, 209 passed, 2 deselected, 4 warnings in 6.85s
FAILED tests/test_directions_cache.py::test_write_and_read_full_round_trip
```

The single failure is the **known, pre-existing** `test_directions_cache::test_write_and_read_full_round_trip` (`timeframeResults` round-trip; `directions_cache.py` is NOT in this diff). Explicitly declared an out-of-scope carry-forward by the spec ("no new failures beyond the known pre-existing red `test_directions_cache`"). This matches the reviewer's verified count (209 passed / 1 known red) exactly. **No new failures introduced.**

Targeted invariant + J-14 runs (all green):
- `test_lookahead.py test_determinism.py test_sandbox.py` → **39 passed** (anti-goal invariants intact)
- `test_auto_session.py -k pinned_path_unchanged` → **1 passed** (pinned path untouched, J-07/J-09 protected)
- `test_auto_session.py -k cost_exceeded` → **5 passed**
- `test_auto_session.py -k "open_universe or screen or promote or staged"` → **16 passed**
- `test_model_rates.py -k cheapest` → **3 passed**

---

## Step 3 — Frontend tests

No dedicated frontend unit-test command is configured for this iteration (display-only, zero FE code change — the `auto-run` render branch renders SCREEN/PROMOTE entries verbatim). The FE render path was confirmed by code inspection (see Browser checks / UI audit).

---

## Step 3.5 — Functional Test Plan results

Live open-universe run (real OpenAI `gpt-5.4-mini` SCREEN + Anthropic `claude-haiku-4-5` PROMOTE), session `bbc379bd-471d-4b2e-8969-afdd98d9bd7a`, budget `{max_iterations:2, max_configs:3, max_tokens:2e6, max_usd:5.0}`, EMA(10/30) crossover NL, dates 2024-01-01→2024-03-01. Terminal state: `budget-exhausted`, 3 configs screened, 1 promoted, tokens 9913, usd $0.0061, wall-clock 142s.

| Test ID | Name | Type | Expected | Actual | Verdict | Notes |
|---------|------|------|----------|--------|---------|-------|
| TC-01 | `cheapest_model()` min-rate | api(unit) | returns min-rate model (`gpt-5.4-mini`) | 3 passed | **PASS** | `test_model_rates.py -k cheapest` |
| TC-02 | Stage routing: SCREEN cheap+noWF, PROMOTE strong+WF | api(hermetic) | SCREEN wfv=False+cheap; PROMOTE wfv=True+strong | 16 passed incl. `test_open_universe_stage_routing_screen_cheap_no_wf_promote_strong_wf` | **PASS** | Live nodes confirm: 3 SCREEN nodes `modelUsed=gpt-5.4-mini`, `walkForwardStatus=None`; 1 PROMOTE node `modelUsed=claude-haiku-4-5`, `walkForwardStatus=complete` |
| TC-03 | k < number screened (k=1) | api(hermetic) | exactly DEFAULT_PROMOTE_K=1 promoted, <screened | `test_open_universe_promotes_exactly_default_k_of_many_screened` passed | **PASS** | Live: 1 WF-bearing node < 3 screened nodes |
| TC-04 | Best WFE-gated from promoted only | api(hermetic) | best is promoted/WFE-gated, never screened-only | `test_open_universe_best_is_wfe_gated_not_highest_return` passed | **PASS** | Live: highest screened raw-return (ETH +0.097) was the one promoted; best=None because the promoted WF candidate did not clear the WFE gate — the correct gated outcome (screened-only never eligible) |
| TC-05 | Stop honored mid-SCREEN & mid-PROMOTE | api(hermetic) | `stopped`, no further node, best preserved | `..._stop_request_transitions_to_stopped_mid_screen`, `..._stop_during_promote_preserves_best` passed | **PASS** | both stop-timing scenarios covered |
| TC-06 | Hard budget across stages (J-13) | api(hermetic) | `budget-exhausted`, no unit past cap | `test_open_universe_stops_at_token_cap_no_config_after`, `..._stops_at_usd_cap` passed | **PASS** | Live run also halted `budget-exhausted` at configs 3/3 with spend ≤ cap |
| TC-07 | J-12 invariants preserved | api(hermetic) | ≥2 distinct configs as nodes; terminal in budget | `test_open_universe_explores_distinct_configs_and_marks_best`, `..._terminal_at_max_configs` passed | **PASS** | Live: 3 distinct configs (BTC/1h, ETH/1h, BTC/4h) surfaced as nodes |
| TC-08 | `cost_exceeded()` cost-caps only | api(unit) | True only on token/usd/wall-clock, not configs | `test_cost_exceeded_ignores_configs_and_iterations_caps` + 4 more passed | **PASS** | 5 cost_exceeded tests green; `exceeded()` semantics unchanged |
| TC-09 | Error cases (per-config/all-fail/degenerate) | api(hermetic) | non-fatal skip; all-fail clean; single promotes | `..._single_config_failure_is_non_fatal`, `..._all_configs_fail_terminates_cleanly`, `..._degenerate_single_config_screen_promotes_it`, `..._promote_failure_is_non_fatal_best_none` passed | **PASS** | all four edge cases covered |
| TC-10 | Route validation: one-of symbol/timeframe → 400 | api(live) | HTTP 400 ambiguous | HTTP 400 + "Provide BOTH 'symbol' and 'timeframe'…" | **PASS** | (test-plan's bare curl returned 422 only because it omitted required `budget`/dates — pydantic fires first; with a complete body the route's 400 fires, route behavior unchanged) |
| TC-11 | Anti-goal invariant suite green | api(hermetic) | invariants pass; only known red | 209 passed / 1 known red; lookahead+determinism+sandbox 39 passed | **PASS** | matches reviewer-verified count |
| TC-12 | Browser: SCREEN/PROMOTE legible in Activity Log | browser | both stages distinguishable; lineage | Pixels not captured (FE down); backend-endpoint substitute fully verified both stage headers + per-candidate entries + node modelUsed/WF + lineage | **PASS (via sanctioned fallback)** | See Browser checks |
| TC-13 | Browser: J-08 live chips + J-10 reload survival | browser | chips increment; state survives reload | Pixels not captured (FE down); live counter progression captured across 12 polls; re-fetch confirms durable terminal state | **PASS (via sanctioned fallback)** | See Browser checks |
| TC-14 | Artifact: handoff + additive blueprint | artifact | handoff present; blueprint additive; no reapproval | dev+frontend handoffs present; blueprint open-universe row updated additively (J-14 staging), no reapproval flag, no nav change (6 ins/3 del) | **PASS** | |

**14/14 test cases passed** (TC-12/TC-13 via the spec-sanctioned backend-endpoint substitute with recorded health-check).

### J-14 backend-endpoint evidence (the exact records the UI renders)

Activity Log (`GET /api/sessions/{id}` → `activityLog`, `type:"auto-run"`):
```
SCREEN — screening 3 seed config(s) on gpt-5.4-mini, no walk-forward.
SCREEN — BTC/USDT 1h: score -0.0898        (→ node 14dd0b6e)
SCREEN — ETH/USDT 1h: score +0.0972        (→ node 5b52da19)
SCREEN — BTC/USDT 4h: score +0.0660        (→ node 652d3400)
PROMOTE — escalating top-1 of 3 to claude-haiku-4-5 + walk-forward.
```
Iteration nodes (`iterationHistory`):
```
14dd0b6e parent=None       gpt-5.4-mini     wfStatus=None       (SCREEN, no WF)
5b52da19 parent=None       gpt-5.4-mini     wfStatus=None       (SCREEN, no WF)
652d3400 parent=None       gpt-5.4-mini     wfStatus=None       (SCREEN, no WF)
4de659e2 parent=5b52da19   claude-haiku-4-5 wfStatus=complete   (PROMOTE, WF ran; child of highest-scored screened node)
```
Confirms: cheap model + no-WF on SCREEN; stronger model + WF on PROMOTE; k=1 < N=3; screen→promote lineage (promoted node's parent is the top-scored screened node); best=None is the correct WFE-gated outcome (promoted candidate didn't clear the gate). No secrets present in any entry.

Evidence files: `reports/qa/goal-financial_free-iter-4-evidence/` — `J14-screen-promote-evidence.json`, `J14-final-session-snapshot.json`, `J08-live-counter-progression.json`, `J10-reload-refetch.json`, `TC12-chrome-fe-unreachable.png`.

---

## Step 4 — Browser checks (Chrome MCP)

**Live-service health-check trail (recorded as required by spec):**
- Pre-run: FE `:3692` → **200**, BE `:8691/health` → **200**.
- During run (12 polls, 8s apart): BE **200** throughout; FE **200** at polls 1–2, then **000** from poll 3 onward.
- Post-run probes: FE **000** ×3; `ss -ltnp` → **NO LISTENER on :3692**; no `/tmp/qa-frontend-8691.log`; no vite process bound to 3692.
- Chrome MCP `navigate http://localhost:3692/session/<id>` → "This site can't be reached" (consistent with the no-listener state, **not** the hidden-tab render throttle).

**Assessment:** the QA-managed frontend genuinely went down mid-window (no listener) — an infrastructure/environment condition, not an application defect; the backend (the single source of truth) stayed healthy the entire time. Per qa.md ("Do NOT mark FAIL just because browser checks were skipped / frontend not running"; "Browser SKIPPED + tests passing = overall PASS"), and honoring the documented headless render-throttle memory, the J-14 / J-08 / J-10 journeys were verified through the exact backend endpoints the UI polls (`GET /api/sessions/{id}` → `autoRun` + `activityLog` + `iterationHistory`):

- **J-14** — SCREEN/PROMOTE stage headers + per-candidate entries + staged node `modelUsed`/`walkForwardStatus` + lineage all present (see evidence above). The FE `ActivityLogEntry` `auto-run` branch (`apps/frontend/src/components/ActivityLogEntry.tsx:27-34`) renders `entry.content` verbatim (Zap icon, violet text), so these entries render legibly once FE is serving — zero FE change, as designed.
- **J-08** — token/USD/configs counters incremented live across polls (configs 0→1→2→3; tokens 0→2389→4750→7130→9913; usd $0→$0.0061), captured in `J08-live-counter-progression.json`. The USD jump on the final poll reflects the stronger PROMOTE model accruing more per the rate table on the one tracker.
- **J-10** — re-fetching `GET /api/sessions/{id}` after termination (what a browser reload re-requests) returns the identical persisted `autoRun` terminal state (status `budget-exhausted`, configs 3/3, tokens 9913, 4 nodes) → durable-store persistence survives reload.

**Pixel-layer carry-forward debt (J-08/J-10/J-14) remains technically uncaptured** because the FE process was not serving during this window — the dedicated browser-qa-agent / a manual operator should re-confirm pixels once `:3692` is reliably up. This does not block the verdict per the rules above; the journeys are functionally proven at the endpoint layer.

---

## Step 4b — UI Evolution Audit

1. **Did the UI evolve to reflect the new capability?** Yes — the Activity Log gains distinct SCREEN/PROMOTE stage entries (cheap model + "no walk-forward" + count; "top-k of N" + stronger model + "walk-forward"), rendered by the existing `auto-run` branch verbatim. Promoted cards carry the stronger `modelUsed` + a walk-forward section; screened cards the cheap model + none.
2. **Can the user see/understand/control it?** See + understand: yes (legible staged entries + node lineage in the tree). Control: unchanged by design — J-14 is observed on the existing API-triggered open-universe run (no new control this iteration, per spec).
3. **Relying on old generic pages?** No new page needed; the Activity Log is J-14's already-reserved blueprint home.
4. **Technically complete but underexposed?** No — the stage content is present in the canonical records and the render branch is confirmed; the only gap is live-pixel capture blocked by FE infra (not a product gap).

**Verdict:** UI-PASS

(Caveat noted, not failing: live pixels were not captured this window due to the FE process being down — render path confirmed in code + content confirmed in the canonical records.)

---

## Blockers

None. The single red test (`test_directions_cache`) is a documented, out-of-scope, pre-existing failure unchanged by this diff.

---

## Notes

- No servers were started by QA (backend/frontend are runner-managed); nothing to tear down. The live open-universe run is terminal (`budget-exhausted`).
- Live run cost: ~$0.006, 9.9k tokens, 142s — comparable to prior iter-3 live QA, as the spec anticipated.
- Reviewer notes carried for the release-manager: the `incredible_auto_dev/scripts/automation/demo*.sh` working-tree changes are unrelated framework tooling, not part of the J-14 feature.
