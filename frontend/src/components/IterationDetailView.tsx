import { useState } from 'react'
import { ArrowLeft, Check, ChevronDown, ChevronRight, Code, Copy, GitCompare } from 'lucide-react'
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
  const [showDiff, setShowDiff] = useState(true)
  const [copied, setCopied] = useState(false)

  function copyScript() {
    if (!iteration.scriptCode) return
    navigator.clipboard.writeText(iteration.scriptCode).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  const canDiff = !!(previousIteration?.scriptCode && iteration.scriptCode)
  const diffResult = canDiff && showDiff
    ? diffLines(previousIteration!.scriptCode, iteration.scriptCode)
    : null

  const result = iteration.result
  const rating = iteration.rating

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
            {((result.total_return ?? 0) * 100).toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="p-4 lg:p-6 space-y-4 lg:space-y-6">
        {/* Backtest parameters */}
        {iteration.params && (
          <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
            <dl className="flex flex-wrap gap-x-6 gap-y-2">
              <div>
                <dt className="text-xs text-slate-400">Symbol</dt>
                <dd className="text-sm font-medium text-slate-700">{iteration.params.symbol}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-400">Timeframe</dt>
                <dd className="text-sm font-medium text-slate-700">{iteration.params.timeframe}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-400">Date Range</dt>
                <dd className="text-sm font-medium text-slate-700">{iteration.params.start_date} – {iteration.params.end_date}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-400">Capital</dt>
                <dd className="text-sm font-medium text-slate-700">${iteration.params.initial_capital.toLocaleString()}</dd>
              </div>
            </dl>
          </div>
        )}

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
              {codeExpanded && (
                <button
                  onClick={copyScript}
                  className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-l border-slate-200 transition-colors text-slate-500 hover:text-slate-700 hover:bg-slate-50"
                >
                  {copied ? (
                    <><Check className="w-3.5 h-3.5 text-emerald-500" /><span className="text-emerald-500">Copied</span></>
                  ) : (
                    <><Copy className="w-3.5 h-3.5" />Copy</>
                  )}
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

        {/* Margin Call Warning Banner */}
        {result.margin_called && (
          <div className="bg-red-50 border border-red-300 rounded-xl px-4 py-3 flex items-start gap-3">
            <span className="text-red-500 text-lg leading-none flex-shrink-0">⚠️</span>
            <div>
              <p className="text-sm font-semibold text-red-700">Margin Call — Account Liquidated</p>
              <p className="text-xs text-red-600 mt-0.5">Loss exceeded 100% of capital. The position was force-closed. Reduce leverage or tighten stop-losses.</p>
            </div>
          </div>
        )}

        {/* Leverage Comparison */}
        {result.unleveraged_return != null && (iteration.params?.leverage ?? 1) > 1 && (() => {
          const unlevRet = result.unleveraged_return as number
          const leverage = iteration.params!.leverage as number
          const leverageEffect = result.total_return - unlevRet
          return (
            <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Leverage Effect ({leverage}x)</h3>
              <div className="grid grid-cols-3 gap-2">
                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-1">Leveraged Return</p>
                  <p className={`text-sm font-bold ${result.total_return >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                    {result.total_return >= 0 ? '+' : ''}{(result.total_return * 100).toFixed(2)}%
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-1">Unleveraged (1x)</p>
                  <p className={`text-sm font-bold ${unlevRet >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                    {unlevRet >= 0 ? '+' : ''}{(unlevRet * 100).toFixed(2)}%
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-500 mb-1">Leverage Effect</p>
                  <p className={`text-sm font-bold ${leverageEffect >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                    {leverageEffect >= 0 ? '+' : ''}{(leverageEffect * 100).toFixed(2)}%
                  </p>
                </div>
              </div>
            </div>
          )
        })()}

        {/* vs Benchmark (Alpha) — visible only when rating data is available */}
        {rating && (
          <div className="grid grid-cols-1 gap-3">
            <MetricsCard
              label="vs Benchmark (Alpha)"
              value={`${(((result.total_return ?? 0) - rating.benchmark_total_return) * 100) >= 0 ? '+' : ''}${(((result.total_return ?? 0) - rating.benchmark_total_return) * 100).toFixed(2)}%`}
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
              value={`${(result.total_return ?? 0) >= 0 ? '+' : ''}${((result.total_return ?? 0) * 100).toFixed(2)}%`}
              variant={result.total_return >= 0 ? 'positive' : 'negative'}
            />
            <MetricsCard
              label="Max Drawdown"
              value={`-${((result.max_drawdown ?? 0) * 100).toFixed(2)}%`}
              variant="negative"
            />
            <MetricsCard
              label="Win Rate"
              value={`${((result.win_rate ?? 0) * 100).toFixed(1)}%`}
              variant={result.win_rate >= 0.5 ? 'positive' : 'neutral'}
            />
            <MetricsCard
              label="Total Trades"
              value={result.num_trades.toString()}
              variant="neutral"
            />
            <MetricsCard
              label="Sharpe Ratio"
              value={(result.sharpe_ratio ?? 0).toFixed(2)}
              variant={result.sharpe_ratio >= 1 ? 'positive' : 'neutral'}
            />
            <MetricsCard
              label="Profit Factor"
              value={result.profit_factor === Infinity ? 'N/A' : (result.profit_factor ?? 0).toFixed(2)}
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
