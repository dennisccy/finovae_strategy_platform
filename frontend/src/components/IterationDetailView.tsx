import { useState } from 'react'
import { ArrowLeft, ChevronDown, ChevronRight, Code, GitCompare } from 'lucide-react'
import type { IterationNode } from '../hooks/useBacktest'
import { RatingPanel } from './RatingPanel'
import { MetricsCard } from './MetricsCard'
import { EquityChart } from './EquityChart'
import { TradesTable } from './TradesTable'
import { diffLines, type DiffLine } from '../utils/scriptDiff'

interface IterationDetailViewProps {
  iteration: IterationNode
  previousIteration?: IterationNode
  onBack: () => void
}

function DiffView({ lines }: { lines: DiffLine[] }) {
  return (
    <div className="text-xs font-mono bg-slate-900 text-slate-100 p-4 overflow-x-auto max-h-72 overflow-y-auto">
      {lines.map((line, i) => (
        <div
          key={i}
          className={
            line.type === 'added'
              ? 'bg-emerald-900/40 text-emerald-300'
              : line.type === 'removed'
              ? 'bg-red-900/40 text-red-300 line-through'
              : 'text-slate-400'
          }
        >
          <span className="select-none mr-2 text-slate-600">
            {line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' '}
          </span>
          {line.text}
        </div>
      ))}
    </div>
  )
}

export function IterationDetailView({ iteration, previousIteration, onBack }: IterationDetailViewProps) {
  const [codeExpanded, setCodeExpanded] = useState(false)
  const [showDiff, setShowDiff] = useState(false)
  const hasMultipleTf = iteration.timeframeResults && iteration.timeframeResults.filter(r => r.status === 'complete').length > 1
  const [selectedTf, setSelectedTf] = useState<string>(
    iteration.timeframeResults?.[0]?.timeframe ?? ''
  )

  const canDiff = !!(previousIteration?.scriptCode && iteration.scriptCode)
  const diffResult = canDiff && showDiff
    ? diffLines(previousIteration!.scriptCode, iteration.scriptCode)
    : null

  // Determine which result/rating to render based on selected TF tab
  const activeTfResult = hasMultipleTf
    ? iteration.timeframeResults.find(r => r.timeframe === selectedTf && r.status === 'complete')
    : null
  const result = activeTfResult?.result ?? iteration.result
  const rating = activeTfResult?.rating ?? iteration.rating

  if (!result) return null

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      {/* Header */}
      <div className="px-4 py-3 lg:px-6 lg:py-4 bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <button
              onClick={onBack}
              className="p-1 text-slate-400 hover:text-slate-600 transition-colors flex-shrink-0"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="min-w-0">
              <h2 className="text-base lg:text-lg font-semibold text-slate-800 truncate">
                {iteration.strategyName}
              </h2>
              <p className="text-xs text-slate-500 truncate">
                {iteration.prompt.length > 50 ? iteration.prompt.slice(0, 50) + '...' : iteration.prompt}
              </p>
            </div>
          </div>
          <div
            className={`px-2.5 py-1 rounded-full text-xs font-medium flex-shrink-0 ${
              result.total_return >= 0
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-red-100 text-red-700'
            }`}
          >
            {result.total_return >= 0 ? '+' : ''}
            {(result.total_return * 100).toFixed(2)}%
          </div>
        </div>
      </div>

      {/* Timeframe tab bar */}
      {hasMultipleTf && (
        <div className="px-4 lg:px-6 bg-white border-b border-slate-200">
          <div className="flex gap-0.5 -mb-px">
            {iteration.timeframeResults
              .filter(r => r.status === 'complete')
              .map(tfr => {
                const isActive = selectedTf === tfr.timeframe
                const ret = tfr.result?.total_return
                return (
                  <button
                    key={tfr.timeframe}
                    onClick={() => setSelectedTf(tfr.timeframe)}
                    className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                      isActive
                        ? 'border-primary-600 text-primary-700'
                        : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                    }`}
                  >
                    {tfr.timeframe}
                    {ret !== undefined && ret !== null && (
                      <span className={`ml-1.5 ${ret >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {ret >= 0 ? '+' : ''}{(ret * 100).toFixed(1)}%
                      </span>
                    )}
                  </button>
                )
              })}
          </div>
        </div>
      )}

      <div className="p-4 lg:p-6 space-y-4 lg:space-y-6">
        {/* Collapsible code preview with diff toggle */}
        {iteration.scriptCode && (
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="flex items-center">
              <button
                onClick={() => setCodeExpanded(!codeExpanded)}
                className="flex-1 flex items-center gap-2 px-4 py-3 hover:bg-slate-50 transition-colors text-left"
              >
                <Code className="w-4 h-4 text-slate-500" />
                <span className="text-sm font-medium text-slate-700 flex-1">Strategy Script</span>
                {codeExpanded ? (
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                )}
              </button>
              {codeExpanded && canDiff && (
                <button
                  onClick={() => setShowDiff(!showDiff)}
                  className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-l border-slate-200 transition-colors ${
                    showDiff
                      ? 'text-primary-600 bg-primary-50'
                      : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <GitCompare className="w-3.5 h-3.5" />
                  {showDiff ? 'Full' : 'Diff'}
                </button>
              )}
            </div>
            {codeExpanded && (
              <div className="border-t border-slate-200">
                {showDiff && diffResult ? (
                  <DiffView lines={diffResult} />
                ) : (
                  <pre className="text-xs bg-slate-900 text-slate-100 p-4 overflow-x-auto max-h-72 overflow-y-auto">
                    <code>{iteration.scriptCode}</code>
                  </pre>
                )}
              </div>
            )}
          </div>
        )}

        {/* vs Benchmark (Alpha) — visible only when rating data is available */}
        {rating && (
          <div className="grid grid-cols-1 gap-3">
            <MetricsCard
              label="vs Benchmark (Alpha)"
              value={`${((result.total_return - rating.benchmark_total_return) * 100) >= 0 ? '+' : ''}${((result.total_return - rating.benchmark_total_return) * 100).toFixed(2)}%`}
              variant={(result.total_return - rating.benchmark_total_return) >= 0 ? 'positive' : 'negative'}
            />
          </div>
        )}

        {/* Rating Panel or Metrics Grid */}
        {rating ? (
          <RatingPanel rating={rating} />
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 lg:gap-4">
            <MetricsCard
              label="Total Return"
              value={`${result.total_return >= 0 ? '+' : ''}${(result.total_return * 100).toFixed(2)}%`}
              variant={result.total_return >= 0 ? 'positive' : 'negative'}
            />
            <MetricsCard
              label="Max Drawdown"
              value={`-${(result.max_drawdown * 100).toFixed(2)}%`}
              variant="negative"
            />
            <MetricsCard
              label="Win Rate"
              value={`${(result.win_rate * 100).toFixed(1)}%`}
              variant={result.win_rate >= 0.5 ? 'positive' : 'neutral'}
            />
            <MetricsCard
              label="Total Trades"
              value={result.num_trades.toString()}
              variant="neutral"
            />
            <MetricsCard
              label="Sharpe Ratio"
              value={result.sharpe_ratio.toFixed(2)}
              variant={result.sharpe_ratio >= 1 ? 'positive' : 'neutral'}
            />
            <MetricsCard
              label="Profit Factor"
              value={result.profit_factor === Infinity ? 'N/A' : result.profit_factor.toFixed(2)}
              variant={result.profit_factor >= 1.5 ? 'positive' : 'neutral'}
            />
          </div>
        )}

        {/* Equity Curve */}
        <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3 lg:mb-4">Equity Curve</h3>
          <EquityChart data={result.equity_curve} />
        </div>

        {/* Trades Table */}
        <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3 lg:mb-4">
            Trade History ({result.trades.length} trades)
          </h3>
          <TradesTable trades={result.trades} />
        </div>
      </div>
    </div>
  )
}
