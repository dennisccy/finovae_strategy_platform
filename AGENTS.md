# AGENTS.md — Finovae Strategy Platform Agent Team Definition

## Team Roster

| ID | Role | Owned Paths | Skills |
|----|------|-------------|--------|
| **A0** | Lead Orchestrator / Judge | `/*` (orchestration, final approval) | overall orchestration, contract freeze approval, cross-agent conflict resolution |
| **A1** | Architect + Contracts | `/docs/**`, `/shared/contracts.py` (draft only, merge requires A0 approval) | architecture, spec-writing, api-contracts |
| **A2** | Data + Backtest Core | `/data/**`, `/backtest/**` | pandas, time-series-data, backtesting, quant-metrics |
| **A3** | Strategy Compiler | `/strategy/**` | prompt-engineering, dsl-design, codegen |
| **A4** | Backend + Sandbox + Runs | `/backend/**` | fastapi, python-sandboxing, security-review, api-contracts |
| **A5** | Frontend React+TS+Vite | `/frontend/**` | react-vite, typescript, charting |
| **A6** | Quant QA / Audit | `/tests/**` | testing, pytest, quant-audit, security-review |

---

## WORKFLOW RULES

### 1. Plan-First

Every agent **must** post a short plan (scope, files touched, approach, estimated risk) **before** editing any files. The plan is addressed to A0. No code changes are permitted until A0 explicitly approves the plan. Plans should be concise — a few bullet points, not a design document.

**Format:**

```
PLAN — A<n> — <short title>
Scope   : <what this task accomplishes>
Files   : <list of files to create or modify>
Approach: <1-3 sentences>
Risk    : <low | medium | high> — <why>
Depends : <task IDs or "none">
```

A0 responds with `APPROVED`, `REVISE <feedback>`, or `BLOCKED <reason>`.

### 2. Strict File Ownership

Each agent edits **only** files within their owned directories (see Ownership Map below). Cross-folder edits require **explicit written approval from A0** in the form:

```
CROSS-EDIT APPROVED — A<requester> may edit <file> (owned by A<owner>) for <reason>.
```

Shared read access is unrestricted — any agent may read any file to understand interfaces and contracts.

### 3. Artefacts Only

Every completed task must include an artefact block containing all four sections:

```
ARTEFACT — A<n> — <task ID>
(a) Diff Summary  : <files changed, lines added/removed, nature of change>
(b) Commands Run  : <exact shell commands executed>
(c) Results       : <test output, build output, or confirmation of manual verification>
(d) Risks / Next  : <known limitations, follow-up work, or "none">
```

Incomplete artefacts will be returned by A0 for revision.

### 4. Freeze Shared Contracts

`/shared/contracts.py` is the **frozen interface contract** for the platform. After A0 marks it as stable:

- **No agent** may modify it without a formal change request reviewed and approved by A0.
- A1 drafts proposed changes. A0 evaluates impact across all agents before approving.
- Any approved change triggers a mandatory review by A2, A3, A4, and A6 to confirm their modules still conform.

The freeze exists to prevent interface churn. Work **within** the existing contracts whenever possible.

---

## GLOBAL ACCEPTANCE CRITERIA (v0.1)

All criteria below must pass before any release is tagged.

### Determinism
- The same inputs (strategy description, symbol, timeframe, date range, initial capital) must produce **identical** trades and equity series across **5 consecutive runs**.
- The backtest engine uses a controlled random seed for slippage modeling; no other source of non-determinism is permitted.

### No Lookahead
- The `signal(df, i)` function receives a DataFrame sliced to `[0:i+1]` — it **cannot** access future bars.
- Signals generated at bar `i` execute at bar `i+1` open (next-bar execution model).
- `tests/test_lookahead.py` must pass with zero violations.

### Sandbox Security
- Strategy code executes inside a RestrictedPython sandbox.
- **Blocked:** network access, arbitrary file I/O, `exec`/`eval`, `__import__`, `open()`, `os` module.
- **Allowed:** numpy, pandas, basic math operations.
- **Limits:** 30-second timeout per signal call (Unix: SIGALRM, Windows: polling).
- `tests/test_sandbox.py` must pass with zero violations.

### UI Layout
- **Left panel:** chat interface for entering natural-language strategy descriptions.
- **Right panel:** results display — equity chart, metrics summary, trade list.
- Each backtest run receives a unique `run_id`.
- Run history is accessible and browsable.

### Required Outputs
Every completed backtest must return:

| Output | Type |
|--------|------|
| Total return | `float` (percentage) |
| Max drawdown | `float` (percentage) |
| Number of trades | `int` |
| Win rate | `float` (percentage) |
| Equity curve | `list[EquityPoint]` |
| Trades list | `list[Trade]` |
| Logs | `list[str]` |

---

## TASK GRAPH

### Phase 0 — Foundation (no dependencies)

| Task | Agent | Description | Depends |
|------|-------|-------------|---------|
| **T0.1** | A1 | Define and freeze `shared/contracts.py` — all data classes, enums, request/response types | — |
| **T0.2** | A1 | Write `shared/schemas.py` — Pydantic schemas derived from contracts | T0.1 |
| **T0.3** | A5 | Scaffold frontend project (React + Vite + TypeScript + Tailwind) with two-panel layout | — |

### Phase 1 — Core Pipeline (depends on Phase 0)

| Task | Agent | Description | Depends |
|------|-------|-------------|---------|
| **T1.1** | A2 | Implement `data/binance_client.py` — Binance REST OHLCV fetcher | T0.1 |
| **T1.2** | A2 | Implement `data/loader.py` — caching layer (Parquet in `.cache/ohlcv/`) | T1.1 |
| **T1.3** | A2 | Implement `data/validation.py` — gap detection, duplicate removal, monotonicity checks | T1.2 |
| **T1.4** | A3 | Implement `strategy/compiler.py` — NL-to-StrategySpec via Claude API | T0.1 |
| **T1.5** | A3 | Implement `strategy/codegen.py` — StrategySpec-to-Python signal function | T0.1, T1.4 |
| **T1.6** | A3 | Implement `strategy/indicators.py` — technical indicator registry | T0.1 |
| **T1.7** | A2 | Implement `backtest/engine.py` — core loop with next-bar execution | T0.1, T1.3 |
| **T1.8** | A2 | Implement `backtest/fills.py` — slippage and commission models | T0.1 |
| **T1.9** | A2 | Implement `backtest/metrics.py` — Sharpe, Sortino, max drawdown, win rate, etc. | T0.1, T1.7 |

### Phase 2 — Integration (depends on Phase 1)

| Task | Agent | Description | Depends |
|------|-------|-------------|---------|
| **T2.1** | A4 | Implement `backend/sandbox.py` — RestrictedPython executor with timeout/memory limits | T0.1, T1.5 |
| **T2.2** | A4 | Implement `backend/pipeline.py` — orchestrate full NL-to-results workflow | T1.1-T1.9, T2.1 |
| **T2.3** | A4 | Implement `backend/api.py` — FastAPI endpoints (`/api/run-backtest`, `/api/runs`, etc.) | T0.2, T2.2 |
| **T2.4** | A5 | Implement `ChatPanel` component — NL input, parameter controls | T0.3 |
| **T2.5** | A5 | Implement `ResultsPanel` component — equity chart (Recharts), metrics, trade list | T0.3 |
| **T2.6** | A5 | Implement `useBacktest` hook — API integration, state management, run history | T2.3, T2.4, T2.5 |
| **T2.7** | A6 | Write `tests/test_lookahead.py` — lookahead prevention invariant tests | T1.7, T2.1 |
| **T2.8** | A6 | Write `tests/test_determinism.py` — 5-run identical output tests | T2.2 |
| **T2.9** | A6 | Write `tests/test_sandbox.py` — sandbox security tests (blocked imports, I/O, network) | T2.1 |

### Phase 3 — Hardening & Polish (depends on Phase 2)

| Task | Agent | Description | Depends |
|------|-------|-------------|---------|
| **T3.1** | A6 | Full integration test — NL description through to rendered results | T2.1-T2.9 |
| **T3.2** | A4 | Error handling pass — graceful failures, user-facing error messages | T2.3 |
| **T3.3** | A5 | UI polish — loading states, error displays, responsive layout | T2.6 |
| **T3.4** | A2 | Performance pass — data caching efficiency, engine hot paths | T2.2 |
| **T3.5** | A0 | v0.1 acceptance review — verify all global acceptance criteria | T3.1-T3.4 |

### Dependency Graph (simplified)

```
Phase 0:  T0.1 ──> T0.2
          T0.3 (parallel)

Phase 1:  T0.1 ──> T1.1 ──> T1.2 ──> T1.3 ──> T1.7 ──> T1.9
          T0.1 ──> T1.4 ──> T1.5
          T0.1 ──> T1.6
          T0.1 ──> T1.8

Phase 2:  T1.5 ──> T2.1 ──> T2.2 ──> T2.3 ──> T2.6
          T0.3 ──> T2.4 ──> T2.6
          T0.3 ──> T2.5 ──> T2.6
          T1.7, T2.1 ──> T2.7
          T2.2 ──> T2.8
          T2.1 ──> T2.9

Phase 3:  T2.* ──> T3.1-T3.4 ──> T3.5
```

---

## OWNERSHIP MAP

| Directory / File | Owner | Notes |
|------------------|-------|-------|
| `/shared/contracts.py` | A1 (draft) / A0 (approve) | FROZEN after approval — changes require A0 sign-off |
| `/shared/schemas.py` | A1 | Pydantic schemas derived from contracts |
| `/shared/**` (other) | A1 | Any additional shared utilities |
| `/docs/**` | A1 | Architecture docs, ADRs, specs |
| `/data/**` | A2 | Binance client, loader, validation |
| `/backtest/**` | A2 | Engine, fills, metrics |
| `/strategy/**` | A3 | Compiler, codegen, indicators |
| `/backend/**` | A4 | API, pipeline, sandbox |
| `/frontend/**` | A5 | React app, components, hooks, styles |
| `/tests/**` | A6 | All test files |
| `/pyproject.toml` | A0 | Dependency and project configuration |
| `/package.json` (root) | A0 | If present, root-level scripts |
| `/.env*` | A0 | Environment configuration |
| `/CLAUDE.md` | A0 | Agent instructions |
| `/AGENTS.md` | A0 | This file |

---

## CONVENTIONS

- **Branch naming:** `a<n>/<task-id>-<short-description>` (e.g., `a2/t1.7-backtest-engine`)
- **Commit messages:** `[A<n>] T<x.y>: <imperative description>` (e.g., `[A2] T1.7: implement next-bar execution engine`)
- **PR titles:** same format as commit messages
- **Reviews:** A0 reviews all PRs. Domain experts review as needed (e.g., A6 reviews anything touching test invariants).
