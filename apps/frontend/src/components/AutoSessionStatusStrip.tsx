import { Loader2, CheckCircle2, AlertTriangle, Square, AlertCircle, Award } from 'lucide-react'
import type { AutoRunStatus, AutoRunStatusValue } from '../lib/sessionApi'

interface AutoSessionStatusStripProps {
  autoRun: AutoRunStatus | null
}

// Status → visual treatment. Colors follow the established light theme and the
// status-color semantics in the plan: running = info/active, criteria-met =
// success, budget-exhausted/interrupted = warning, stopped = neutral, error =
// danger. A subtle spinner marks the active state.
const STATUS_META: Record<AutoRunStatusValue, {
  label: string
  wrap: string
  badge: string
  Icon: typeof Loader2
  spin?: boolean
}> = {
  queued:             { label: 'Queued',           wrap: 'bg-blue-50 border-blue-200',       badge: 'bg-blue-100 text-blue-700',       Icon: Loader2, spin: true },
  running:            { label: 'Running',          wrap: 'bg-blue-50 border-blue-200',       badge: 'bg-blue-100 text-blue-700',       Icon: Loader2, spin: true },
  'criteria-met':     { label: 'Criteria met',     wrap: 'bg-emerald-50 border-emerald-200', badge: 'bg-emerald-100 text-emerald-700', Icon: CheckCircle2 },
  'budget-exhausted': { label: 'Budget exhausted', wrap: 'bg-amber-50 border-amber-200',     badge: 'bg-amber-100 text-amber-700',     Icon: AlertTriangle },
  interrupted:        { label: 'Interrupted',      wrap: 'bg-amber-50 border-amber-200',     badge: 'bg-amber-100 text-amber-700',     Icon: AlertTriangle },
  stopped:            { label: 'Stopped',          wrap: 'bg-slate-50 border-slate-200',     badge: 'bg-slate-200 text-slate-600',     Icon: Square },
  error:              { label: 'Error',            wrap: 'bg-red-50 border-red-200',         badge: 'bg-red-100 text-red-700',         Icon: AlertCircle },
}

const STOP_REASON_LABEL: Record<string, string> = {
  'criteria-met': 'Robust targets met',
  'budget-exhausted': 'Budget exhausted',
  stopped: 'Stopped by user',
  interrupted: 'Interrupted (worker restart)',
  error: 'Run error',
}

/**
 * Compact status strip for an automated (backend Auto Run) session, pinned at
 * the top of the Iterations panel. Reads the canonical autoRun block (single
 * source of truth) — run state, budget counters, stop reason, and the marked
 * best iteration. Renders nothing for a manual session (no autoRun).
 */
export function AutoSessionStatusStrip({ autoRun }: AutoSessionStatusStripProps) {
  if (!autoRun) return null

  const meta = STATUS_META[autoRun.status] ?? STATUS_META.running
  const Icon = meta.Icon
  const { budget } = autoRun
  const isActive = autoRun.status === 'queued' || autoRun.status === 'running'
  const wallClock = Math.round(budget.wallClockSec)
  const maxWallClock = budget.maxWallClockSec != null ? Math.round(budget.maxWallClockSec) : null
  const showSecondRow = Boolean(autoRun.bestIterationId) || (!isActive && Boolean(autoRun.stopReason))

  return (
    <div className={`mb-3 rounded-lg border px-3 py-2 ${meta.wrap}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold ${meta.badge}`}>
          <Icon className={`w-3.5 h-3.5 ${meta.spin ? 'animate-spin' : ''}`} />
          {meta.label}
        </span>

        <span className="text-xs text-slate-500">
          {isActive ? 'Optimizing server-side' : 'Automated session'}
        </span>

        {/* Budget counters (read from the canonical autoRun.budget) */}
        <span className="ml-auto flex items-center gap-2 text-xs text-slate-500">
          <span title="Improvement rounds done / max">
            {budget.iterationsDone}/{budget.maxIterations} rounds
          </span>
          <span className="text-slate-300">·</span>
          <span title="Elapsed / max wall-clock (seconds)">
            {wallClock}s{maxWallClock != null ? ` / ${maxWallClock}s` : ''}
          </span>
        </span>
      </div>

      {showSecondRow && (
        <div className="mt-1.5 flex items-center gap-2 flex-wrap text-xs">
          {autoRun.bestIterationId && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-violet-100 text-violet-700 font-medium">
              <Award className="w-3 h-3" />
              Best: {autoRun.bestIterationId.slice(0, 8)}
            </span>
          )}
          {!isActive && autoRun.stopReason && (
            <span className="text-slate-500">
              {STOP_REASON_LABEL[autoRun.stopReason] ?? autoRun.stopReason}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
