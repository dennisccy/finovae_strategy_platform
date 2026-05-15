# AGENTS.md — Finovae Strategy Platform Frontend Agent Team Definition

## Monorepo Context

This roster scopes the **frontend package only**, which now lives at
`apps/frontend/` inside the **finovae_strategy_platform monorepo** (previously a
standalone repo). **Path notes for the tables below:**

- `/frontend/**` → `apps/frontend/**` (the Vite/React app).
- `CLAUDE.md`, `AGENTS.md`, `CODEOWNERS` are at `apps/frontend/`. `apps/frontend/CODEOWNERS`
  is informational only — GitHub honors CODEOWNERS solely at `/`, `/.github/`, `/docs/`.
- `vercel.json` is at the **repo root**, not in `apps/frontend/`; `.gitignore` is the
  repo-root file; `apps/frontend/.env.example` is the per-app env template.
- The FastAPI backend is a sibling package at `apps/backend/` (its own `AGENTS.md`);
  this team does not own it.
- The stack is started from the repo root via `./scripts/dev.sh` /
  `./scripts/start-frontend.sh`; the shared scripts drive Vite through
  `apps/frontend/tools/next-shim/` (see `apps/frontend/CLAUDE.md`).
- Repo-level governance (root `README.md`, `docs/goal.md`, the
  `incredible_auto_dev` subtree and root symlinks) is handled by the
  `incredible_auto_dev` dev-chain, **not** by this roster.

## Team Roster

| ID | Role | Owned Paths | Skills |
|----|------|-------------|--------|
| **A0** | Lead Orchestrator / Judge | `/*` (orchestration, final approval) | overall orchestration, cross-agent conflict resolution |
| **A5** | Frontend React+TS+Vite | `/frontend/**` | react-vite, typescript, charting |

---

## WORKFLOW RULES

### 1. Plan-First

Every agent **must** post a short plan (scope, files touched, approach, estimated risk) **before** editing any files. The plan is addressed to A0. No code changes are permitted until A0 explicitly approves the plan.

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

### 2. Artefacts Only

Every completed task must include an artefact block containing all four sections:

```
ARTEFACT — A<n> — <task ID>
(a) Diff Summary  : <files changed, lines added/removed, nature of change>
(b) Commands Run  : <exact shell commands executed>
(c) Results       : <test output, build output, or confirmation of manual verification>
(d) Risks / Next  : <known limitations, follow-up work, or "none">
```

---

## GLOBAL ACCEPTANCE CRITERIA

### UI Layout
- **Left panel:** chat interface for entering natural-language strategy descriptions.
- **Right panel:** results display — equity chart, metrics summary, trade list.
- Each backtest run receives a unique `run_id`.
- Run history is accessible and browsable.

---

## OWNERSHIP MAP

| Directory / File | Owner | Notes |
|------------------|-------|-------|
| `/frontend/**` | A5 | React app, components, hooks, styles |
| `/CLAUDE.md` | A0 | Agent instructions |
| `/AGENTS.md` | A0 | This file |
| `/CODEOWNERS` | A0 | Code review automation |
| `/.env.example` | A0 | Environment configuration |
| `/.gitignore` | A0 | Git ignore rules |
| `/vercel.json` | A0 | Vercel deployment config |

---

## CONVENTIONS

- **Branch naming:** `a<n>/<task-id>-<short-description>` (e.g., `a5/t3.3-responsive-layout`)
- **Commit messages:** `[A<n>] T<x.y>: <imperative description>` (e.g., `[A5] T3.3: make frontend responsive for mobile`)
- **PR titles:** same format as commit messages
- **Reviews:** A0 reviews all PRs.
