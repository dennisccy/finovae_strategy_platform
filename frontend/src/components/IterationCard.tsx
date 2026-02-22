import { Trash2, Loader2 } from 'lucide-react'
import type { IterationNode } from '../hooks/useBacktest'

interface IterationCardProps {
  iteration: IterationNode
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  isLatest?: boolean
}

function timeAgo(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime()
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

const statusConfig = {
  generating: { label: 'Generating', dotClass: 'bg-blue-400 animate-pulse', bgClass: 'bg-blue-50 border-blue-200' },
  executing: { label: 'Executing', dotClass: 'bg-amber-400 animate-pulse', bgClass: 'bg-amber-50 border-amber-200' },
  complete: { label: 'Complete', dotClass: 'bg-emerald-500', bgClass: 'bg-white border-slate-200' },
  error: { label: 'Error', dotClass: 'bg-red-500', bgClass: 'bg-red-50 border-red-200' },
}

export function IterationCard({ iteration, onSelect, onDelete, isLatest = false }: IterationCardProps) {
  const config = statusConfig[iteration.status]
  const isInProgress = iteration.status === 'generating' || iteration.status === 'executing'
  const isComplete = iteration.status === 'complete'
  const isPast = !isLatest && isComplete

  const formatReturn = (value: number) => {
    const pct = (value * 100).toFixed(2)
    return value >= 0 ? `+${pct}%` : `${pct}%`
  }

  // Compact view for past iterations
  if (isPast) {
    return (
      <div
        className="border border-slate-200 rounded-lg px-3 py-2 bg-white hover:bg-slate-50 transition-colors group cursor-pointer"
        onClick={() => onSelect(iteration.id)}
      >
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <h4 className="text-xs font-semibold text-slate-700 truncate">
                {iteration.strategyName}
              </h4>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className={`font-medium ${iteration.totalReturn >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {formatReturn(iteration.totalReturn)}
              </span>
              <span className="text-slate-300">·</span>
              <span>{iteration.numTrades} trades</span>
              <span className="text-slate-300">·</span>
              <span>{timeAgo(iteration.timestamp)}</span>
            </div>
          </div>
          <div className="flex items-center gap-1 ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(iteration.id) }}
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
      className={`border rounded-xl p-4 transition-colors ${config.bgClass} ${isComplete ? 'cursor-pointer hover:shadow-md' : ''}`}
      onClick={isComplete ? () => onSelect(iteration.id) : undefined}
    >
      {/* Status badge + timestamp */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${config.dotClass}`} />
          <span className="text-xs font-medium text-slate-600">{config.label}</span>
        </div>
        <span className="text-xs text-slate-400">{timeAgo(iteration.timestamp)}</span>
      </div>

      {/* Strategy name */}
      <h4 className="text-sm font-semibold text-slate-800 truncate">
        {iteration.strategyName || 'Generating...'}
      </h4>

      {/* Prompt (truncated) */}
      <p className="text-xs text-slate-500 mt-0.5 truncate">
        {iteration.prompt.length > 60 ? iteration.prompt.slice(0, 60) + '...' : iteration.prompt}
      </p>

      {/* Metrics row (when complete) */}
      {iteration.status === 'complete' && iteration.result && (
        <div className="flex items-center gap-3 mt-2.5 text-xs">
          <span className={`font-semibold ${iteration.totalReturn >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
            {formatReturn(iteration.totalReturn)}
          </span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-600">{iteration.numTrades} trades</span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-600">WR {(iteration.winRate * 100).toFixed(0)}%</span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-600">SR {iteration.sharpe.toFixed(2)}</span>
        </div>
      )}

      {/* Multi-TF badges */}
      {iteration.timeframeResults && iteration.timeframeResults.length > 1 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {iteration.timeframeResults.map(tfr => {
            const badgeColors = {
              pending: 'bg-slate-100 text-slate-400',
              running: 'bg-amber-100 text-amber-700 animate-pulse',
              complete: 'bg-emerald-100 text-emerald-700',
              error: 'bg-red-100 text-red-700',
            }
            return (
              <span
                key={tfr.timeframe}
                className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${badgeColors[tfr.status]}`}
              >
                {tfr.timeframe}
                {tfr.status === 'complete' && tfr.result && (
                  <> {tfr.result.total_return >= 0 ? '+' : ''}{(tfr.result.total_return * 100).toFixed(1)}%</>
                )}
              </span>
            )
          })}
        </div>
      )}

      {/* Loading indicator */}
      {isInProgress && (
        <div className="flex items-center gap-2 mt-2.5">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-400" />
          <span className="text-xs text-slate-500">
            {iteration.status === 'generating'
              ? 'AI is crafting your strategy...'
              : iteration.activeTimeframe && iteration.timeframeResults.length > 1
                ? `Running ${iteration.activeTimeframe}... (${iteration.timeframeResults.filter(r => r.status === 'complete' || r.status === 'running').length}/${iteration.timeframeResults.length})`
                : 'Running backtest...'}
          </span>
        </div>
      )}

      {/* Error message */}
      {iteration.status === 'error' && iteration.error && (
        <p className="text-xs text-red-600 mt-2 truncate">{iteration.error}</p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 mt-3 pt-2.5 border-t border-slate-100">
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(iteration.id) }}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors ml-auto"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Delete
        </button>
      </div>
    </div>
  )
}
