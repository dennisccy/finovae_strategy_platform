# Phase goal-money-billions-iter-1 — UX Regression Review

**Date:** 2026-05-18

**Verdict:** UX-REGRESSION-PASS

> **Scope note.** The phase spec's goal-mode metadata is `Frontend Present: no`
> (zero frontend code changed; `git diff HEAD -- apps/frontend` empty). `plan.md`
> deliberately sets `Frontend Present: yes` **only** to force the DoD-mandated
> browser **regression** of existing journeys — not because new UI exists. The
> trivial "backend-only, no review required" shortcut is therefore not the right
> treatment: this iteration rewrites the OHLCV cache and the session-store
> persistence layer *beneath* six existing user journeys, so the substantive
> UX-regression question — *did any existing journey break?* — is live and was
> evaluated against the browser-QA evidence below.

## New Capability Discoverability

No new user-facing capability was added. `user-visible-changes.md` is explicit:
"None. No new user action or capability was added." There is no new screen,
route, component, navigation entry, button, field, or displayed data. The set of
things a user can do is byte-identical to the prior iteration.

Consequently there is **nothing to assess for discoverability** — no
0-click/1-click/2-click path needs to be checked because no feature was
introduced. The lone internal change without a UI (the `clear_cache()`
correctness fix) was never user-invokable before this iteration either, so it is
not a newly-hidden capability (correctly classified under "Not Visible Yet" in
`user-visible-changes.md`).

## Regression Risk

The only prior goal-mode iteration is **iter-0**, which was **verify-only (zero
source changes)** — it built no UI and touched no component. There is therefore
**no shared-frontend-component regression vector** (no frontend file changed in
iter-0 or iter-1; `ui-surface-map.md` confirms 0 modified components, 0
navigation changes, 0 new routes).

The real regression vector is the **backing data/persistence layer** consumed by
existing journeys. Mapping changed backend modules → dependent journeys:

| Changed module | Journeys backed | Regression watch | Browser-QA outcome |
|---|---|---|---|
| `data/loader.py` (per-day CSV → single Parquet; covering-cache; partial merge; atomic write) | J-01 (cold backtest), J-06 (warm re-run), J-03 (walk-forward multi-window fetch) | **High** (loader path is central) | J-01 → UT-02 **PASS**; J-06 → UT-03 **PASS** (byte-identical warm re-run, single `BTC_USDT/1h.parquet`, no per-day fan-out); J-03 → UT-06 **PASS** (WFE 1.15 ✓, 2 windows, combined OOS curve) |
| `session_store.py` (`BASE_DIR` default `/tmp` → durable `<repo>/.data/backtests`) | J-02 (open prior run), J-06 history, refresh persistence | **High** (spec-flagged: "key persistence-layer regression watch") | J-02 → UT-04 **PASS** (prior run reloads full detail from durable store, no 404/blank/zeros); refresh persistence → UT-10 **PASS** (history survives F5, served server-side, localStorage empty) |
| `data/loader.py` data feeding insights | J-04 (AI insights) | Medium (downstream of loader) | J-04 → UT-07 **PASS** (20 ranked suggestion pills) |

Browser QA result: **10/11 PASS, 0 FAIL, 1 SKIPPED**. Every DoD journey (J-01,
J-02, J-03, J-04, J-06) plus robustness (UT-08/UT-09) and discoverability
(UT-11) verified green through the running UI. **No prior user journey
regressed** — including the spec's highest-risk persistence path (J-02), which
was directly exercised via both prior-run reload (UT-04) and cross-refresh
persistence (UT-10).

**Documented, non-blocking deviation (not a defect):** UT-06 ran walk-forward at
IS/OOS 3/1 instead of the plan's 6/3 because the UT-02 reference range
(2023-01-01→2023-06-01, ~5 months) cannot form a 9-month window — a test-plan
data-range tension, not a product regression. Journey J-03's assertions (WFE
badge + ≥1 window row + combined OOS curve) were truthfully satisfied.

## UI vs Backend Parity

`implementation-summary.md` items (single-file Parquet cache, smart partial
top-up, crash-safe atomic writes, durable-by-default history, `clear_cache()`
correctness) are **all intentionally backend-only and user-invisible by explicit
phase design** ("New user-facing capability: None."). There is **no backend
capability that should be surfaced in the UI but isn't** — the phase goal is
invariant hardening beneath unchanged journeys, not feature delivery. No parity
gap.

## Flags

### Hidden Capabilities
- None. No capability was added, so none can be hidden.

### Undiscoverable Capabilities
- None. No new entry point was needed; existing journeys are unchanged and were
  re-verified discoverable (UT-11 PASS).

### Potential Regressions
- **None observed.** All loader-backed and session-store-backed journeys
  (J-01/J-02/J-03/J-04/J-06) verified PASS through the browser; the
  highest-risk persistence path (J-02) is clean via UT-04 + UT-10. The
  cold-vs-warm determinism invariant held byte-identically through the UI
  (UT-03).

### Visual Consistency
- N/A — zero frontend code changed; no new pages, components, tokens, effects,
  or layouts. The existing two-panel UI renders correctly (UT-01 app shell,
  recharts equity curves drawn, tables populated). No DESIGN-SYSTEM deviation
  is possible because nothing visual was added or restyled.

## Residual (informational — already escalated by browser-QA, not a UX regression)

UT-05 — the *new* restart-durability guarantee (J-02 history survives a backend
restart with **no** `BACKTEST_STORE_DIR` / no `.env`) — was **SKIPPED**, not
failed: executing it required a destructive infra op (kill the shared QA backend
+ move `apps/backend/.env`) that the environment-safety policy denied with no
interactive user to authorize. This is **not a UX regression** and is out of
this reviewer's adjudication scope for three reasons:

1. It is verification of a *new* behavioral guarantee, not breakage of an
   *existing* journey. Pre-existing durability (the actual regression question)
   is intact and confirmed by UT-04 + UT-10.
2. The deterministic gate for this exact behavior is owned by functional pytest
   **TC-08/TC-09** (`test_session_store.py`), reported **3 passed** in the dev
   handoff (BASE_DIR absolute & not `/tmp` with env unset; write →
   simulated-restart re-resolve → read-back intact).
3. Browser-QA already escalated it explicitly to the auditor/goal-evaluator with
   strong on-disk + code corroboration.

It does not change the UX-regression verdict.

## Recommendation

**No action required for UX regression.** The UI correctly remained unchanged
for a deliberately user-invisible storage-layer iteration; no existing user
journey regressed (all five DoD journeys + refresh persistence + discoverability
PASS through the browser, 0 FAIL); there is no hidden capability, no
discoverability gap, and no UI-vs-backend parity gap. Defer the UT-05
restart-durability *verification-method* gap to the auditor/goal-evaluator as
already routed by browser-QA (gated deterministically by `test_session_store.py`
TC-08/TC-09, passing) — it is not a regression of any prior user journey.
