# Phase goal-auto-money-printer-iter-3 — User-Visible Changes

**Phase:** goal-auto-money-printer-iter-3
**Date:** 2026-05-19
**Written by:** ui-impact-analyst

---

## What Users Can Now Do

- **Start a fully headless strategy *search* with one API call that names no
  market.** `POST /api/auto-sessions` with only an objective (`"robust"`) and a
  budget — **no symbol, no timeframe** — now succeeds (previously this was
  rejected). The created session appears in the existing session list/sidebar
  as an "Auto: …" session and opens in the normal two-panel session view.
- **Watch a headless run explore several different market configurations
  live.** Once the open-universe session is opened, the session's iteration
  tree fills with **≥2 distinct configurations** (different trading pair and/or
  candle size, e.g. one config on one pair/timeframe, another on a different
  one) as they are explored — rendered exactly like manually-run iterations,
  with the existing robust-best `BestBadge` marking the winner.
- **See exactly how much budget a headless run spent, in the run status bar.**
  The existing automated-run status strip (`AutoRunBar`) now shows a compact
  spend readout: AI tokens used, US-dollar cost, and number of configurations
  explored (e.g. `12,480 tok · $0.0193 · 3 cfg`). It updates live while the run
  is active and persists after a browser reload.
- **Tell at a glance when a run stopped because it hit its budget.** A run that
  ends by reaching its hard spending cap now shows a visually distinct
  amber status with a dollar-circle icon and the text "Automated run complete ·
  budget reached · X/Y iterations" — clearly different from a green
  "robust targets met" finish or a red "stopped" run.

---

## What Changed in the Visible UI

- **The automated-run status strip (`AutoRunBar`, shown at the top of the
  session view for any server-driven auto-session) now has a right-aligned
  spend readout.** Format: `<tokens> tok · $<usd> · <n> cfg`, in tabular
  (monospaced-digit) figures, dimmed (`opacity-75`), with a hover tooltip
  "AI tokens / USD / configs spent under the hard budget". It appears only when
  the session has recorded spend; it is completely hidden for older sessions,
  manual sessions, and just-created sessions (the bar looks exactly as before
  in those cases — no `NaN`/`undefined`).
- **The `budget-exhausted` terminal state in `AutoRunBar` is now its own
  visual style.** It renders amber (`bg-amber-50 border-amber-200
  text-amber-700`) with a `CircleDollarSign` icon and the message "Automated
  run complete · budget reached · X/Y iterations". Previously a
  budget-exhausted finish reused the generic green "complete" style and was
  indistinguishable at a glance from a criteria-met finish.
- **No new page, panel, route, leaderboard, button, menu item, or form was
  added.** The open-universe configs surface through the **existing** iteration
  tree / iteration cards / `BestBadge` with no change to those components. The
  only net-new pixels are inside the existing `AutoRunBar` strip.

---

## What Old Behavior Changed

- **`POST /api/auto-sessions` open-universe request:** previously *any* request
  that omitted symbol/timeframe was rejected with HTTP 422 ("Open-universe
  search … is not yet supported"). Now, omitting **both** symbol and timeframe
  together with a valid `objective` + `budget` starts an open-universe search
  (HTTP 200). A pinned request (symbol + timeframe supplied) still validates
  and behaves byte-for-byte as before; a half-specified request (e.g. timeframe
  but no symbol) is still a clean 422; an unsupported `objective` value or a
  malformed budget/date is still a clean 422 (never a 500).
- **Every automated run — including the existing pinned auto-sessions — now
  records spend and is bounded by the immutable cost tracker.** Default
  token/USD/config limits are deliberately high and finite, so a normal pinned
  run's stopping point and behaviour are unchanged; only an explicitly tiny
  budget changes when a run stops. Existing pinned auto-sessions will now also
  show the spend readout in `AutoRunBar` once they record spend.
- **`AutoRunBar` budget-exhausted appearance changed** (see above): a run that
  ends on budget now looks amber/distinct instead of green/generic. Testers
  re-verifying the auto-session status strip should expect the new amber
  treatment for budget-reached finishes; `criteria-met` (green) and `stopped`
  (red) are unchanged.

---

## Not Visible Yet

- **The configured budget *caps* are recorded but not displayed.** The durable
  spend record includes the cap limits (`caps.aiTokens`, `caps.usd`,
  `caps.configs`, `caps.wallClockSeconds`), but `AutoRunBar` shows only the
  amounts *spent*, not "spent of allowed" (e.g. it shows `12,480 tok`, not
  `12,480 / 20,000 tok`). The remaining-budget headroom is in the API data but
  has no UI rendering this iteration.
- **Wall-clock spend is captured but not shown in the bar.** `wallClockSeconds`
  is persisted in the spend record and typed in the frontend, but the readout
  renders only tokens / USD / configs — elapsed wall-clock time is not
  displayed.
- **`history_scope` request field has no visible effect.** It is accepted and
  persisted with the session, but its cross-run *learning* behaviour is a later
  iteration (J-15); nothing in the UI reflects or uses it yet.
- **Open-universe has no UI trigger control (intentional, not a gap).** Starting
  an open-universe search is API-only (`POST /api/auto-sessions` with objective
  + budget); per the phase spec there is deliberately no new UI button/form for
  it. The *results* are fully visible via the existing UI; only the *trigger*
  is API-side by design.
