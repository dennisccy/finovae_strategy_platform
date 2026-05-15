import { useState } from 'react'
import { Trash2, RotateCw, Zap } from 'lucide-react'
import type { IterationNode } from '../hooks/useBacktest'

interface IterationCardProps {
  iteration: IterationNode
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onRerun?: (id: string) => void
  onStartAutoRun?: (id: string) => void
  isLatest?: boolean
}

function formatLondonTime(timestamp: string): string {
  const d = new Date(timestamp)
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/London',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).formatToParts(d)
  const get = (type: string) => parts.find(p => p.type === type)?.value ?? '00'
  return `${get('year')}-${get('month')}-${get('day')} ${get('hour')}:${get('minute')}:${get('second')}`
}

const statusConfig = {
  generating: { label: 'Generating', dotClass: 'bg-blue-400 animate-pulse', bgClass: 'bg-blue-50 border-blue-200' },
  executing: { label: 'Executing', dotClass: 'bg-amber-400 animate-pulse', bgClass: 'bg-amber-50 border-amber-200' },
  complete: { label: 'Complete', dotClass: 'bg-emerald-500', bgClass: 'bg-white border-slate-200' },
  error: { label: 'Error', dotClass: 'bg-red-500', bgClass: 'bg-red-50 border-red-200' },
}

export function IterationCard({ iteration, onSelect, onDelete, onRerun, onStartAutoRun, isLatest = false }: IterationCardProps) {
  const [pendingDelete, setPendingDelete] = useState(false)
  const config = statusConfig[iteration.status]
  const isInProgress = iteration.status === 'generating' || iteration.status === 'executing'
  const isComplete = iteration.status === 'complete'
  const isPast = !isLatest && isComplete

  const formatReturn = (value: number) => {
    const pct = (value * 100).toFixed(2)
    return value >= 0 ? `+${pct}%` : `${pct}%`
  }

  // Compact view for past or in-progress iterations
  if (isPast || isInProgress) {
    return (
      <div
        className={`relative border rounded-lg px-3 py-2 transition-colors group ${isPast ? 'bg-white hover:bg-slate-50 cursor-pointer border-slate-200' : config.bgClass}`}
        onClick={() => isPast ? onSelect(iteration.id) : undefined}
      >
        {pendingDelete && (
          <div
            className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-white/95 rounded-lg backdrop-blur-sm"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="text-sm font-medium text-slate-700">Delete this iteration?</p>
            <div className="flex gap-2">
              <button
                onClick={() => setPendingDelete(false)}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => onDelete(iteration.id)}
                className="px-3 py-1.5 text-xs font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        )}
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <div className={`w-1.5 h-1.5 rounded-full ${config.dotClass}`} />
              <h4 className="text-xs font-semibold text-slate-700 truncate">
                {iteration.strategyName || (iteration.status === 'generating' ? 'AI crafting strategy...' : 'Executing...')}
              </h4>
            </div>

            {/* Show prompt snippet if still generating/executing and no strategyName yet */}
            {isInProgress && !iteration.strategyName && iteration.prompt && (
              <p className="text-[10px] text-slate-500 truncate mb-0.5 ml-3.5">
                {iteration.prompt.length > 50 ? iteration.prompt.slice(0, 50) + '...' : iteration.prompt}
              </p>
            )}

            {iteration.changeSummary && (
              <p className="text-[10px] italic text-slate-400 truncate mb-0.5 ml-3.5">
                {iteration.changeSummary}
              </p>
            )}
            {iteration.params && (
              <p className="text-[10px] text-slate-400 truncate mb-0.5 ml-3.5">
                {iteration.params.symbol} · {iteration.params.timeframe} · {iteration.params.start_date}–{iteration.params.end_date} · ${iteration.params.initial_capital.toLocaleString()}
              </p>
            )}
            <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
              <span className={`font-medium ${(iteration.totalReturn ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {formatReturn(iteration.totalReturn ?? 0)}
              </span>
              {iteration.rating && (
                <>
                  <span className="text-slate-300">·</span>
                  <span className={`font-medium ${((iteration.totalReturn ?? 0) - iteration.rating.benchmark_total_return) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                    {((iteration.totalReturn ?? 0) - iteration.rating.benchmark_total_return) >= 0 ? '+' : ''}{(((iteration.totalReturn ?? 0) - iteration.rating.benchmark_total_return) * 100).toFixed(2)}% vs BM
                  </span>
                </>
              )}
              {isPast && (
                <>
                  <span className="text-slate-300">·</span>
                  <span>{iteration.numTrades ?? 0} trades</span>
                  {(iteration.numTrades ?? 0) < 50 && (
                    <span className="text-amber-500" title="Low sample size — fewer than 50 trades">⚠</span>
                  )}
                  <span className="text-slate-300">·</span>
                  <span className="text-red-500">DD {((iteration.maxDrawdown ?? 0) * 100).toFixed(1)}%</span>
                  <span className="text-slate-300">·</span>
                  <span>WR {((iteration.winRate ?? 0) * 100).toFixed(0)}%</span>
                  <span className="text-slate-300">·</span>
                  <span>SR {(iteration.sharpe ?? 0).toFixed(2)}</span>
                  {iteration.walkForwardStatus === 'complete' && iteration.walkForwardResult && (
                    <>
                      <span className="text-slate-300">·</span>
                      <span className={
                        iteration.walkForwardResult.wfe >= 0.5
                          ? 'text-emerald-600'
                          : iteration.walkForwardResult.wfe >= 0.3
                          ? 'text-amber-500'
                          : 'text-red-500'
                      }>
                        WFE {iteration.walkForwardResult.wfe.toFixed(2)}
                      </span>
                    </>
                  )}
                </>
              )}
              {isInProgress && (
                <>
                  <span className="text-slate-300">·</span>
                  <span className="text-slate-500 italic">{config.label}</span>
                </>
              )}
              <span className="text-slate-300">·</span>
              <span>{formatLondonTime(iteration.timestamp)}</span>
            </div>
          </div>
          <div className="flex items-center gap-1 ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
            {(iteration.status === 'complete' || iteration.status === 'error') && onRerun && (
              <button
                onClick={(e) => { e.stopPropagation(); onRerun(iteration.id) }}
                className="p-1.5 text-slate-400 hover:text-primary-600 hover:bg-primary-50 rounded transition-colors"
                title="Rerun"
              >
                <RotateCw className="w-3.5 h-3.5" />
              </button>
            )}
            {iteration.status === 'complete' && onStartAutoRun && (
              <button
                onClick={(e) => { e.stopPropagation(); onStartAutoRun(iteration.id) }}
                className="p-1.5 text-slate-400 hover:text-violet-600 hover:bg-violet-50 rounded transition-colors"
                title="Auto Run"
              >
                <Zap className="w-3.5 h-3.5" />
              </button>
            )}
            <button
              onClick={(e) => { e.stopPropagation(); setPendingDelete(true) }}
              className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
              title="Delete"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Full view for latest/active iteration
  return (
    <div
      className={`relative border rounded-xl p-4 transition-colors ${config.bgClass} ${isComplete ? 'cursor-pointer hover:shadow-md' : ''}`}
      onClick={isComplete ? () => onSelect(iteration.id) : undefined}
    >
      {pendingDelete && (
        <div
          className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-white/95 rounded-xl backdrop-blur-sm"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="text-sm font-medium text-slate-700">Delete this iteration?</p>
          <div className="flex gap-2">
            <button
              onClick={() => setPendingDelete(false)}
              className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => onDelete(iteration.id)}
              className="px-3 py-1.5 text-xs font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors"
            >
              Delete
            </button>
          </div>
        </div>
      )}
      {/* Status badge + timestamp */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${config.dotClass}`} />
          <span className="text-xs font-medium text-slate-600">{config.label}</span>
        </div>
        <span className="text-xs text-slate-400">{formatLondonTime(iteration.timestamp)}</span>
      </div>

      {/* Strategy name */}
      <h4 className="text-sm font-semibold text-slate-800 truncate">
        {iteration.strategyName || 'Generating...'}
      </h4>

      {/* Change summary */}
      {iteration.changeSummary && (
        <p className="text-xs italic text-slate-400 mt-0.5 truncate">
          {iteration.changeSummary}
        </p>
      )}

      {/* Prompt (truncated) */}
      {!iteration.changeSummary && (
        <p className="text-xs text-slate-500 mt-0.5 truncate">
          {iteration.prompt.length > 60 ? iteration.prompt.slice(0, 60) + '...' : iteration.prompt}
        </p>
      )}

      {/* Params chip */}
      {iteration.params && (
        <p className="text-xs text-slate-400 mt-0.5 truncate">
          {iteration.params.symbol} · {iteration.params.timeframe} · {iteration.params.start_date}–{iteration.params.end_date} · ${iteration.params.initial_capital.toLocaleString()}
        </p>
      )}

      {/* Metrics row (when complete) */}
      {iteration.status === 'complete' && iteration.result && (
        <div className="flex items-center gap-2 mt-2.5 text-xs flex-wrap">
          <span className={`font-semibold ${(iteration.totalReturn ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
            {formatReturn(iteration.totalReturn ?? 0)}
          </span>
          {iteration.rating && (
            <>
              <span className="text-slate-400">|</span>
              <span className={`font-semibold ${((iteration.totalReturn ?? 0) - iteration.rating.benchmark_total_return) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {((iteration.totalReturn ?? 0) - iteration.rating.benchmark_total_return) >= 0 ? '+' : ''}{(((iteration.totalReturn ?? 0) - iteration.rating.benchmark_total_return) * 100).toFixed(2)}% vs BM
              </span>
            </>
          )}
          <span className="text-slate-400">|</span>
          <span className="text-slate-600">{iteration.numTrades ?? 0} trades</span>
          {(iteration.numTrades ?? 0) < 50 && (
            <span className="text-amber-500" title="Low sample size — fewer than 50 trades">⚠</span>
          )}
          <span className="text-slate-400">|</span>
          <span className="text-red-500">DD -{((iteration.maxDrawdown ?? 0) * 100).toFixed(1)}%</span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-600">WR {((iteration.winRate ?? 0) * 100).toFixed(0)}%</span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-600">SR {(iteration.sharpe ?? 0).toFixed(2)}</span>
          {iteration.walkForwardStatus === 'complete' && iteration.walkForwardResult && (
            <>
              <span className="text-slate-400">|</span>
              <span className={
                iteration.walkForwardResult.wfe >= 0.5
                  ? 'text-emerald-600'
                  : iteration.walkForwardResult.wfe >= 0.3
                  ? 'text-amber-500'
                  : 'text-red-500'
              }>
                WFE {iteration.walkForwardResult.wfe.toFixed(2)}
              </span>
            </>
          )}
        </div>
      )}

      {/* Loading indicator is now handled entirely by the compact view, so we remove it from full view */}

      {/* Error message */}
      {iteration.status === 'error' && iteration.error && (
        <p className="text-xs text-red-600 mt-2 truncate">{iteration.error}</p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 mt-3 pt-2.5 border-t border-slate-100">
        {iteration.status === 'complete' && onStartAutoRun && (
          <button
            onClick={(e) => { e.stopPropagation(); onStartAutoRun(iteration.id) }}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:text-violet-600 hover:bg-violet-50 rounded-lg transition-colors"
          >
            <Zap className="w-3.5 h-3.5" />
            Auto Run
          </button>
        )}
        {(iteration.status === 'complete' || iteration.status === 'error') && onRerun && (
          <button
            onClick={(e) => { e.stopPropagation(); onRerun(iteration.id) }}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
          >
            <RotateCw className="w-3.5 h-3.5" />
            Rerun
          </button>
        )}
        <button
          onClick={(e) => { e.stopPropagation(); setPendingDelete(true) }}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors ml-auto"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Delete
        </button>
      </div>
    </div>
  )
}
