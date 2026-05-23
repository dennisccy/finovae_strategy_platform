# Phase goal-financial_free-iter-4 — User-Visible Changes

**Phase:** goal-financial_free-iter-4 — Staged SCREEN→PROMOTE cost-tiering for the open-universe search (J-14)
**Date:** 2026-05-23
**Written by:** ui-impact-analyst

---

## What Users Can Now Do

<!-- No new control/button this iteration — J-14 is observed on the existing open-universe trigger. The new value is what becomes *visible* on that same run. -->

- On an open-universe automated run (triggered the same way as before — `POST /api/auto-sessions` with no `symbol`/`timeframe`), users can now **watch the optimizer spend cheap-first** in the Left **Activity Log**: a **SCREEN** stage that evaluates several seed configs on the cheapest model with no walk-forward, then a **PROMOTE** stage that escalates only the top-k (k < number screened) to a stronger model + walk-forward.
- Users can now **see which candidates were triaged cheaply vs. promoted to full evaluation** in the Activity Log: a `SCREEN —` header naming the cheap model (`gpt-5.4-mini`) and candidate count, one `SCREEN —` row per screened candidate (symbol/timeframe + robust score), a `PROMOTE —` header ("top-k of N", stronger model, "walk-forward"), and a `PROMOTE —` row for each new WFE-gated best.
- Users can now **trace the screen→promote lineage in the iteration tree** on the Right panel: a promoted iteration card appears as a **child** of the screened candidate it was promoted from (`parentId` linkage).
- Users can now **tell screened from promoted candidates by inspecting the iteration cards**: a promoted card shows the stronger `modelUsed` (e.g. `claude-haiku-4-5`) **and** a walk-forward section; a screened-only card shows the cheap model (`gpt-5.4-mini`) and **no** walk-forward section.
- Users can trust that the **marked "best"** badge on an open-universe run now derives **only** from promoted, walk-forward-gated candidates — a high-raw-return but un-walk-forwarded screened candidate can never be marked best.

---

## What Changed in the Visible UI

- The **Left Activity Log** (`ActivityLogEntry`, `auto-run` entry type) now shows two new stage groups during an open-universe run — `SCREEN —` entries (violet Zap-icon rows) and `PROMOTE —` entries — distinguishable by their text prefixes. No new component; the existing `auto-run` render branch displays the new `content` text verbatim.
- The **Right-panel iteration tree** now shows promoted nodes nested as children of their screened parent, making the cheap-triage → expensive-promote step legible as a parent/child relationship rather than a flat list.
- **Iteration cards** now visibly differ by stage: promoted cards carry the stronger model name + a walk-forward section; screened cards carry the cheap model name + no walk-forward section. (Both are existing card shapes — no card markup changed.)

---

## What Old Behavior Changed

- **Open-universe run model/walk-forward usage:** previously every seed config was evaluated uniformly with walk-forward on the single chosen request model. Now only the top-k promoted survivors get walk-forward + the stronger request model; all other screened configs run on the cheapest model with no walk-forward. Testers re-verifying J-12 should expect distinct configs to **still** appear as iteration cards, but most as cheap/no-WF screened nodes.
- **"Best" marking on open-universe runs:** previously best was selected over all uniformly-evaluated configs. Now best is selected strictly from the promoted (walk-forward-gated) candidates; if no promoted candidate is eligible, best is `None` (a correct gated outcome, not an error). A `/stop` issued before any promote runs therefore legitimately leaves no "best" badge while keeping all screened nodes browsable.
- **Budget meaning:** `max_configs` now caps SCREEN breadth (count of screened candidates). Promote work does not consume new config slots but still accrues real tokens/USD onto the same single budget tracker; the status-strip token/USD/configs values continue to update from that one tracker (no new counter).

---

## Not Visible Yet

- **No new request control** for `screen_model` / `promote_model` / `promote_k` — the staging uses internal defaults (cheapest catalog model for SCREEN, request `model` for PROMOTE, `DEFAULT_PROMOTE_K = 1`); there is no UI to tune k or the per-stage models. (Deliberately out of scope.)
- **Multi-candidate overfit-gating leaderboard (J-16)** is not built — promoted WFE-gated candidates are visible only as individual cards/activity rows, not a ranked leaderboard visualization.
