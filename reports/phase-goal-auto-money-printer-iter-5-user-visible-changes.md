# Phase goal-auto-money-printer-iter-5 — User-Visible Changes

**Phase:** goal-auto-money-printer-iter-5
**Date:** 2026-05-19
**Written by:** ui-impact-analyst

---

## What Users Can Now Do

- A user (or API caller) can run the headless optimizer in **open-universe** mode a
  second time and have it **learn from prior runs**: with `history_scope: "global"`
  (or by omitting it / sending any unrecognised value), the run screens and promotes
  the historically strongest `(symbol, timeframe)` market/timeframe families first
  instead of always walking a fixed exploration order.
- A user can **see *why* the run warm-started**: when learning happens, one
  plain-language note appears at the **top of the selected session's Activity feed**,
  e.g. *"Warm start (global history): prioritising ETH/USDT 1h — prior best robust
  0.78 across 1 prior session"*. It cites the concrete prior-run evidence that drove
  the ordering.
- A user can **opt out of cross-run learning** by sending
  `history_scope: "this-run"` on `POST /api/auto-sessions`: that run ignores all
  prior runs — no warm-start note, no reordering, the same fixed exploration order
  as before.
- A user can start the headless run from a script (no browser) and the new
  **"Auto: …" session still appears in the Sessions dropdown within a few seconds**
  (unchanged discovery behaviour); selecting it shows the warm-start note in its
  Activity feed.

---

## What Changed in the Visible UI

- The selected session's **Activity feed** now shows a new violet ⚡ entry — *"Warm
  start (global history): prioritising `<SYMBOL> <TIMEFRAME>` — prior best robust
  `<score>` across N prior session(s)"* — rendered **at the top of the feed**, above
  the collapsible iteration groups, with its full text visible (not truncated). It
  appears only on a `"global"`/default open-universe run that found usable prior
  promoted history.
- This entry is **visually identical** to the existing automated-run notes the feed
  already renders (same ⚡ icon, same violet styling, same position). **No new page,
  component, route, button, control, or navigation was added** — no frontend code
  changed. A warm-started headless run remains UI-indistinguishable from a manual one.
- No entry appears for: a `"this-run"` (opt-out) run, an open-universe run with no
  usable prior history (empty store), a pinned run, or any legacy session — the feed
  is unchanged in all those cases.

---

## What Old Behavior Changed

- **`history_scope` request field**: previously accepted and saved but had **no
  effect**. Now, on an **open-universe** run, it changes behaviour —
  `"this-run"` opts out of cross-run learning; anything else (including omitting it,
  `null`, `"global"`, or an unrecognised value) enables the read-only warm start.
  The exact value the caller sent is still saved unchanged (omitted stays `null`).
- **Open-universe exploration order**: previously a fixed list on every run. Now,
  when prior promoted history exists and the run is not opted out, that **same
  bounded list is reordered** so the historically best families are screened and
  promoted first. With no usable history (or opted out, or pinned) the order is
  exactly as before — no behaviour change.
- **Durable session record**: an open-universe session now also records the
  *effective* resolved scope (`effectiveHistoryScope`) in its `autoRun` block
  alongside the raw saved `historyScope`. This is returned by
  `GET /api/sessions/{id}` and consumed by the existing live poll, but it is **not
  rendered as a labeled UI element**. Pinned runs record neither key and are
  completely unchanged.

---

## Not Visible Yet

- **`autoRun.effectiveHistoryScope`** — the resolved `"global"`/`"this-run"` value is
  written to the durable record and returned by `GET /api/sessions/{id}`, but there
  is no dedicated UI element that displays this value. The *decision* it represents
  is surfaced indirectly through the warm-start Activity-feed note (on global runs
  with history); the raw key itself is API-/record-only by design (additive key, no
  schema fork, no new control — matches the spec's "no structural UI change").
- **The reordered SCREEN enumeration** is internal: the user observes its *effect*
  (which family is screened/promoted first) and the *citation*, but the reordered
  list is not itself displayed anywhere. Intentional — the spec requires no new UI
  surface for the ordering.
