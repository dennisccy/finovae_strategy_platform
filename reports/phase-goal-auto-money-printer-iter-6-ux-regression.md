# Phase goal-auto-money-printer-iter-6 — UX Regression Review

**Date:** 2026-05-20

**Verdict:** UX-REGRESSION-PASS

---

## Scope of this Iteration

Iter-6 is a deliberately minimal-surface presentation layer over an already-structural backend invariant. The user-visible delta is:

1. A conditional muted `<p>` sub-line beneath the existing emerald `complete` activity-log card, rendering `entry.detail` when present (`ActivityLogEntry.tsx` lines 144–158, +5 net lines).
2. A new backend-emitted `auto-run` row (`Robust-best: <id> selected over <N-1> other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage`) that re-uses the existing violet `Zap`-icon `auto-run` renderer — zero renderer changes.

No new pages, routes, components, navigation entries, badges, polling logic, or state machinery were introduced.

---

## New Capability Discoverability

| Capability | Surface | Click-distance from home | Label clarity | Verdict |
|------------|---------|---------------------------|---------------|---------|
| Per-PROMOTE robust-best rationale (`"Best — WF-validated …"` / `"Not best — <gate>"` / `"Best (sole survivor) — gates not met: …"`) | Muted sub-line on the emerald `complete` row in the Activity Log accordion (expanded PROMOTE iteration group) | 0 clicks to reach session main view; the Activity Log column is always visible. 1 click to expand the iteration accordion if collapsed. Effective **≤ 1 click**. | Plain operator vocabulary — `WFE`, `gate`, `trades`, `walk-forward windows`, `over-leveraged`. Browser QA UT-11 confirmed regex absence of `_GATE_FAIL_PENALTY`, `DEFAULT_MIN_WFE`, `RobustInputs`, `robust_score`, `null`, `undefined`. | Discoverable |
| Terminal `Robust-best: <id> selected over N-1 other promoted candidate(s) — gates: …` summary row | Violet `Zap`-icon `auto-run` row at the bottom of the activity feed (open-universe runs with ≥ 2 PROMOTEs only) | 0 clicks — bottom of the always-visible Activity Log column. **0 clicks**. | Plain English: "Robust-best", "selected over", "gates". Browser QA UT-04 confirmed text and iter-id matching `bestIterationId`. | Discoverable |
| Pre-existing `Best` badge co-location with `Best —` rationale | Amber `Star` pill on the iteration card whose Activity Log sub-line begins `Best —` / `Best (sole survivor) —` | Both surfaces are in the same main session view; the iteration list column and the activity log column are side-by-side. **0 clicks**. | The amber pill already carries the tooltip "Best iteration — selected by the robust walk-forward objective" (iter-1's B3 fix). Pairing with the rationale text strengthens it. Browser QA UT-03 confirmed badge sits on the iteration whose rationale starts with `Best —`. | Discoverable |

**Conclusion:** Every new capability is reachable within ≤ 1 click from the home/session view and uses operator-readable vocabulary. No hidden or undiscoverable capabilities.

---

## Regression Risk — Shared-Component Audit

The iter-6 diff touches exactly **one** frontend file: `ActivityLogEntry.tsx`. This is a shared component used for every activity-log entry type (`auto-run`, `user-prompt`, `ai-step`, `code-preview`, `error`, `complete`, `insights`).

### Surfaces using `ActivityLogEntry.tsx` from prior phases

| Prior phase | Feature | Branch consumed | Risk assessment |
|-------------|---------|-----------------|-----------------|
| iter-1 (J-08, J-09) | Live `AutoRunBar` + `★ Best` pill driven by `bestIterationId`; live polling activity feed | `auto-run` (violet Zap row) | **Low** — `auto-run` branch byte-unchanged. The new terminal `Robust-best:` row uses this exact renderer with no changes. Browser QA UT-10 confirmed `AutoRunBar` numeric spans render finite values (no `NaN`/`Infinity`). |
| iter-2 (J-10, J-11) | Server-driven Auto Run + cooperative Stop; legacy in-browser loop deleted | `auto-run` (Auto Run start/stop markers) | **Low** — `auto-run` branch byte-unchanged. Browser QA UT-04 confirmed Auto Run start/stop violet rows still render correctly alongside the new terminal `Robust-best:` row. |
| iter-3 (J-12, J-13) | Open-universe bounded enumeration + immutable cost tracker; `AutoRunBar` spend readout | `auto-run` (`Exploring config N: SYM TF` markers), `AutoRunBar` (separate component) | **Low** — Auto Run spend readout is in `SessionContainer.tsx`/`AutoRunBar`, **not** touched. `Exploring config` markers (now superseded by SCREEN/PROMOTE prefixes from iter-4) use the same `auto-run` renderer, byte-unchanged. |
| iter-4 (J-14) | SCREEN→PROMOTE staged routing; `SCREEN N done — …` / `PROMOTE config: …` markers with `stage` field on iteration nodes | `auto-run` (stage markers), `complete` (SCREEN/PROMOTE done lines with `stage`-derived prefix in `content`) | **Low** — `complete` renderer change is purely additive (`entry.detail &&` gated). SCREEN `complete` entries do NOT carry `detail` (asserted in browser QA UT-08 and backend unit test). PROMOTE `complete` entries gain the new sub-line — this **is** the new capability. iter-4's top-line `content` (`PROMOTE done — BTC/USDT 4h: …`) renders unchanged inside the wrapping `<div className="flex-1 min-w-0">`. Browser QA UT-02 confirmed the top-line text matches iter-4's emission exactly. |
| iter-5 (J-15) | Read-only global-history warm start + planner-decision `auto-run` citation row | `auto-run` (warm-start citation row) | **Low** — `auto-run` branch byte-unchanged. The warm-start citation row (e.g., `Warm start (global history): prioritising ETH/USDT 1h — prior best robust 0.78 across 1 prior session`) co-exists with the new terminal `Robust-best:` row; both use the violet `Zap` renderer. Browser QA UT-10 confirmed both render in the same feed without conflict. |

### Structural anti-regression confirmation

- **`_run_pinned` byte-unchanged**: backend dev handoff and structural assertions confirm `git diff HEAD -- apps/backend/backend/auto_session.py` shows zero edits inside `_run_pinned` (J-07–J-11 invariant). Browser QA UT-07 confirmed pinned `complete` rows show exactly one `<p>` (no `detail` sub-line) — visually byte-identical to pre-iter-6.
- **SCREEN entries unchanged**: backend never sets `detail` on SCREEN `complete` entries (J-14 invariant). Browser QA UT-08 confirmed SCREEN cards have exactly one `<p>` and contain no `Best`/`Not best`/`sole survivor` substrings.
- **Pre-iter-6 historic activity entries unchanged**: any session whose activity log was written before iter-6 has no `detail` field on `complete` rows; the `entry.detail &&` guard means those rows render byte-identical to today. Browser QA UT-09 confirmed clicking a pre-iter-6 iteration loads its detail panel without rationale sub-lines.
- **`auto-run`, `user-prompt`, `ai-step`, `code-preview`, `error`, `insights` branches byte-unchanged**: `git diff` over `ActivityLogEntry.tsx` shows the *only* change is inside the `complete` branch.

**Conclusion:** No regression risk to any prior-phase feature. All shared-component changes are scoped to the `complete` branch and gated by `entry.detail &&`, leaving non-detail paths byte-identical.

---

## UI vs Backend Parity

| Backend capability | UI exposure | Parity |
|--------------------|-------------|--------|
| `_robust_best_rationale` helper returns one of five rationale shapes | Rendered as the muted sub-line on the PROMOTE `complete` card | **Full** — all five shapes were observed across browser QA sessions: `"Best — WF-validated …"`, `"Not best — WFE … below 0.30 gate"`, `"Best (sole survivor) — gates not met: …"`, and the unit-tested `"under min-trades floor (…)"`, `"no walk-forward windows"`, `"lower robust score (…)"` strings. |
| Terminal-state `Robust-best: <id> selected over N-1 …` emission (open-universe, ≥ 2 PROMOTEs) | Rendered as the existing violet `Zap` `auto-run` row | **Full** — Browser QA UT-04 confirmed exact text and iter-id match. UT-05 confirmed single-PROMOTE runs correctly suppress the row. |
| `"over-leveraged (X.X×)"` reason text | Defined in the helper, unit-tested at helper level | **Intentional non-parity (documented)** — `RobustInputs.leverage` is hard-coded to 1.0 in `_robust_inputs` (`auto_session.py:1072`). Plumbing a `leverage` request parameter is explicitly out of scope (phase spec OUT-OF-SCOPE line). The reason string exists for signature completeness; user-visible-changes.md line 37 documents the gap as "not visible yet". No flag — backend-only-for-signature-completeness is acceptable per the agent rules. |
| `BACKTEST_STORE_DIR` cannot be emptied; cross-round rationale recomputation | Write-time snapshot semantics — earlier PROMOTE row's rationale is not retroactively rewritten when a later promotion changes `best_id` | **Full** — Documented design decision (phase spec line 91, dev handoff lines 96–118). The `Best` badge (driven by live `autoRun.bestIterationId`) and the terminal `Robust-best:` row remain the source of truth for the final chosen winner. Browser QA UT-02 explicitly documented the stale-snapshot edge case (session `f0cdd94b`) and confirmed the audit chain remains intact via badge + terminal row. |

**Conclusion:** All in-scope backend capabilities are surfaced. The single non-parity item (`"over-leveraged"` rationale not exercised by a live engine) is explicitly out-of-scope for this iteration and documented in user-visible-changes.md. No hidden backend capability.

---

## Visual Consistency

| Aspect | Iter-6 implementation | Prior-phase precedent | Verdict |
|--------|------------------------|----------------------|---------|
| Color palette | `text-xs text-emerald-700/70 mt-1` for the muted sub-line; emerald container `bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3` byte-preserved | iter-4's `complete` card uses the same emerald palette; iter-5's warm-start citation uses the same muted-text pattern; iter-1's `AutoRunBar` uses slate/primary/emerald/amber tokens | **Consistent** |
| Typography | Sub-line `text-xs` (12px) / `font-weight 400` / `rgba(4,120,87,0.7)` / `margin-top 4px` — visually subordinate to the 14px/500 top line | iter-5's warm-start citation row used the same muted scale; the `text-xs` muted typography is the established pattern for secondary detail in the activity feed | **Consistent** |
| Iconography | No new icons. `CheckCircle2` for `complete`, `Zap` for the terminal `Robust-best:` row (existing `auto-run` renderer) | iter-1 introduced `Zap`/`CheckCircle2`/`Star`; iter-3 introduced the amber `$` icon for `budget-exhausted`. No new icon needed. | **Consistent** |
| Layout | Wraps the existing `<p>` in `<div className="flex-1 min-w-0">` — same `flex-1 min-w-0` pattern already used in the `insights` branch (line 177) | The `flex-1 min-w-0` wrapper is the established pattern for multi-line content within an icon-prefixed card | **Consistent** |
| DESIGN SYSTEM tokens | All Tailwind utility classes used are from the established scale (`text-xs`, `text-emerald-700/70`, `mt-1`, `bg-emerald-50`, `border-emerald-200`, `rounded-xl`); no arbitrary values | The project uses Tailwind utility classes throughout; no inline styles, no `arbitrary[]` values | **Consistent** |
| Card geometry preservation | Card container classes unchanged (`bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3`); browser QA UT-12 confirmed card height grows by only ~one extra `text-xs` line (~16–20px) | Iter-4's SCREEN/PROMOTE prefix added to `entry.content` similarly grew the top line without changing card geometry | **Consistent** |

**No visual inconsistencies detected.** The new sub-line is faithful to the established design system and mirrors iter-5's warm-start citation pattern precisely.

---

## Flags

### Hidden Capabilities

None.

### Undiscoverable Capabilities

None.

### Potential Regressions

None blocking.

**Informational note (not a flag, recorded for the auditor):** The write-time snapshot semantics mean that, in multi-round open-universe runs where a later PROMOTE unseats an earlier one (e.g., browser QA session `f0cdd94b` where ETH was promoted first then BTC unseated it), both PROMOTE sub-lines may read `Best (sole survivor) — …` because each was written when only one prior PROMOTE was complete. This is the documented and explicitly in-scope-OUT design (phase spec lines 56, 91; OUT OF SCOPE section "Recomputing a prior PROMOTE iteration's `detail` rationale across rounds"). The `Best` badge on `IterationCard` (driven by live `autoRun.bestIterationId`) and the terminal `Robust-best:` row remain the authoritative source of truth for the chosen winner, so the J-16 audit chain is intact. A future iteration could revisit this if operators report confusion.

### Label Confusion

None. Rationale vocabulary (`WFE`, `gate`, `trades`, `walk-forward windows`, `over-leveraged`, `min-trades floor`, `robust score`) is plain operator language matching the spec terminology. Terminal summary text exactly matches the spec ("Robust-best: \<id\> selected over N-1 other promoted candidate(s) — gates: WFE ≥ 0.30, ≥ 5 trades, no over-leverage"). Best badge tooltip "Best iteration — selected by the robust walk-forward objective" is consistent with the new rationale text.

### Visual Consistency

No deviations from the DESIGN SYSTEM. All new typography reuses existing Tailwind tokens (`text-xs`, `text-emerald-700/70`, `mt-1`). No arbitrary CSS values introduced. Card geometry, border, padding, icon size, and color palette are byte-preserved on rows without `detail`, and grow by exactly one muted sub-line on rows with `detail`.

---

## Recommendation

**No action required.** The iter-6 UI evolution is exemplary for an additive presentation-layer iteration:

- Single 5-line frontend diff scoped to one branch of one component.
- Zero new components, no new state, no new polling, no new icons, no new routes, no navigation changes.
- Mirrors iter-4 / iter-5's additive-detail patterns exactly.
- All 12 browser QA tests pass (UT-01 through UT-12), confirming both new capabilities are visible and discoverable while all prior-phase journeys (J-01 through J-15) render unchanged.
- Backend handoff confirms `_run_pinned` byte-unchanged (J-07–J-11 invariant), SCREEN entries unchanged (J-14 invariant), `robust_objective.py`/`shared/contracts.py`/`session_store.py`/`pipeline.py`/`sandbox.py`/`backtest/` all byte-unchanged (J-09/J-16 invariant + anti-goals).
- No hidden or undiscoverable capabilities; UI parity is full for in-scope backend changes.
- Documented out-of-scope item (`"over-leveraged"` not exercised by live engine) is appropriately noted in user-visible-changes.md and is acceptable per the phase spec.

**Verdict:** UX-REGRESSION-PASS
