# J-16 Leaderboard Pixel Evidence — iter-8

This directory holds the **load-bearing browser/pixel proof** that the real
`AutoSessionLeaderboard` component paints its rows — the single remaining gate
for J-16 (and therefore GOAL_ACHIEVED).

## Screenshots

| File | Capture type | What it proves |
|------|--------------|----------------|
| `J-16-leaderboard-seeded-component.png` | (c) seeded deterministic render | **All four DoD elements**, incl. the WFE-failing **rejection**. 3 ranked rows; BEST badge + violet highlight on row #2 (ETH/USDT 1h = `bestIterationId`); color-graded WFE chips (red `WFE 0.10`, emerald `WFE 0.60`, `WFE —`); and row #1's gating reason `WFE 0.10 < 0.30` in red. Row #1 has the **highest** robust score (+0.5450) and return (+90%) yet is **not** best — the overfit gating made visible (the J-16 anti-goal). |
| `J-16-leaderboard-seeded-fullpage.png` | (c) | Same, full app frame (left Activity panel + right Iterations panel with the leaderboard). |
| `J-16-leaderboard-live-run-component.png` | (b) live data | The REAL iter-7 open-universe run (`2a829f6e…`): 3 ranked rows, BEST badge on BTC/USDT 4h, real WFE chips (2.53 / 1.26 emerald, `—` screen), gating reasons. Proves the same component paints genuine live-run data (clears J-08/J-09 live-pixel debt). |
| `J-16-leaderboard-live-run-fullpage.png` | (b) | Same, full app frame. |

Both captures are genuine pixels of the real component rendered through the
normal `GET /api/sessions/{id}` → React render path — NOT an endpoint/JSON
substitute.

## How the pixels were produced

The Chrome-MCP hidden-tab render throttle (a documented environment limit, see
memory `browser-qa-headless-render-throttle`) starves a backgrounded tab's React
scheduler. The remedy is a dedicated, visible browser context — here a
**Playwright** Chromium instance (the same engine `demo_runner.py` uses), which
is not subject to the throttle.

1. `seed_leaderboard_session.py` (run with the backend venv) drives the REAL
   `AutoSessionController` with the hermetic `FakePipeline` against the live file
   store, producing session `j16-leaderboard-proof`. The sequence is the binding
   J-16 fixture (`test_overfit_gating_higher_return_wfe_fail_not_best`): candidate
   A (BTC/USDT 1h, return 0.9, WFE 0.10) → `eligible:false`, "WFE 0.10 < 0.30",
   NOT best; B (ETH/USDT 1h, return 0.3, WFE 0.60) → the marked best; C (BTC/USDT
   4h) → screen-only. This is a real run that writes standard artifacts — not a
   parallel store and not a forked schema; the robust score is the one
   `RobustScorer`'s verbatim output and best is the one `bestIterationId`.
2. `capture_leaderboard.py` (run with system `python3`, which has Playwright 1.58
   + cached Chromium) loads the live app, which auto-opens the most-recently
   accessed session, waits for the leaderboard to paint, asserts the DoD elements
   (and that there is **no uncaught pageerror** — a regression guard for the crash
   fixed this iteration), and screenshots the component + full page.

### Reproduce

```bash
# 1) seed the proof session (idempotent)
cd apps/backend && PYTHONPATH=. .venv/bin/python \
  ../../reports/qa/goal-financial_free-iter-8-evidence/seed_leaderboard_session.py

# 2) capture (system python3)
cd ../.. && python3 \
  reports/qa/goal-financial_free-iter-8-evidence/capture_leaderboard.py J-16-leaderboard-seeded expect_rejection
```

### API relay note

The frontend dev instance currently bound to `:3691` was started with a backend
URL pointing at a dead port, so its built-in Vite `/api` proxy 500s. To capture
against the healthy backend WITHOUT disturbing running services, `capture_leaderboard.py`
relays the browser's same-origin `/api/*` calls to `:8691`. The component, data,
and render path are unchanged — only the transport hop differs. In the automated
pipeline, `browser-qa-phase.sh` self-heals this: after reconciling
`CHAIN_BACKEND_PORT` to the live backend it kills the stale frontend and restarts
it wired to the correct port.

The live-run capture may print relay timeouts for *other, off-screen* sessions
that hydrate after the screenshot is taken; those are cosmetic — the screenshot of
the active session is valid.

## Crash found and fixed (the pixel gate did its job)

The first capture attempt revealed a **genuine crash**: legacy/partial `autoRun`
records in the durable store (pre-`budget`-schema sessions carrying
`currentIteration`/`spend` instead of a `budget` block) caused
`useBacktest.ts` to throw `Cannot read properties of undefined (reading
'iterationsDone')`. Because `App.tsx` mounts a `SessionContainer` (hence a
`useBacktest`) for **every** session, one such record blanked the whole app — so
the leaderboard could never paint. This was invisible to data-layer tests and had
been masked by six consecutive browser-QA SKIPs (the port bug). The minimal fix
(`useBacktest.ts` budget guard + `IterationPanel.tsx` status-strip gate) is
documented in the dev handoff.
