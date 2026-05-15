# AGENTS.md — Finovae Strategy API Agent Team Definition

## Monorepo Context

This roster scopes the **backend package only**, which now lives at `apps/backend/`
inside the **finovae_strategy_platform monorepo** (previously a standalone repo).
**Every `/...` path in the tables below is relative to `apps/backend/`** — e.g.
`/backend/**` means `apps/backend/backend/**`, `/shared/contracts.py` means
`apps/backend/shared/contracts.py`.

- The Vite/React frontend is a sibling package at `apps/frontend/` (its own
  `AGENTS.md`); this team does not own it.
- Backend run/test commands are in `apps/backend/CLAUDE.md`; the stack is started
  from the repo root via `./scripts/dev.sh` / `./scripts/start-backend.sh`.
- `apps/backend/docs/` now contains only `plans/`; the detailed architecture doc
  was relocated to the repo-level `docs/architecture/backend-internals.md`.
- Repo-level governance (root `README.md`, `docs/goal.md`,
  `docs/architecture/overview.md`, the `incredible_auto_dev` subtree and the root
  `CLAUDE.md/config/scripts/templates/tests` symlinks) is handled by the
  `incredible_auto_dev` dev-chain, **not** by this roster. There is no
  `apps/backend/CODEOWNERS` (removed — GitHub does not honor CODEOWNERS outside
  `/`, `/.github/`, `/docs/`); ownership intent is captured by this file.

## Team Roster

| ID | Role | Owned Paths | Skills |
|----|------|-------------|--------|
| **A0** | Lead Orchestrator / Judge | `/*` (orchestration, final approval) | overall orchestration, contract freeze approval, cross-agent conflict resolution |
| **A1** | Architect + Contracts | `/docs/**`, `/shared/contracts.py` (draft only, merge requires A0 approval) | architecture, spec-writing, api-contracts |
| **A2** | Data + Backtest Core | `/data/**`, `/backtest/**` | pandas, time-series-data, backtesting, quant-metrics |
| **A3** | Strategy Compiler | `/strategy/**` | prompt-engineering, dsl-design, codegen |
| **A4** | Backend + Sandbox + Runs | `/backend/**` | fastapi, python-sandboxing, security-review, api-contracts |
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
| `/tests/**` | A6 | All test files |
| `/pyproject.toml` | A0 | Dependency and project configuration |
| `/.env*` | A0 | Environment configuration |
| `/CLAUDE.md` | A0 | Agent instructions |
| `/AGENTS.md` | A0 | This file |

---

## CONVENTIONS

- **Branch naming:** `a<n>/<task-id>-<short-description>` (e.g., `a2/t1.7-backtest-engine`)
- **Commit messages:** `[A<n>] T<x.y>: <imperative description>` (e.g., `[A2] T1.7: implement next-bar execution engine`)
- **PR titles:** same format as commit messages
- **Reviews:** A0 reviews all PRs. Domain experts review as needed (e.g., A6 reviews anything touching test invariants).
