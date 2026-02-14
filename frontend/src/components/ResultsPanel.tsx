import { BacktestResult, StrategySpec, GeneratedScript, StrategyRating } from '../hooks/useBacktest'
import { MetricsCard } from './MetricsCard'
import { EquityChart } from './EquityChart'
import { TradesTable } from './TradesTable'
import { StrategyDisplay } from './StrategyDisplay'
import { RatingPanel } from './RatingPanel'
import { AlertCircle, Loader2, BarChart3, ArrowLeft, Code } from 'lucide-react'

interface ResultsPanelProps {
  result: BacktestResult | null
  rating: StrategyRating | null
  strategySpec: StrategySpec | null
  generatedScript: GeneratedScript | null
  scriptCode: string | null
  isLoading: boolean
  error: string | null
  onBackToReview?: () => void
}

export function ResultsPanel({
  result,
  rating,
  strategySpec,
  generatedScript,
  scriptCode,
  isLoading,
  error,
  onBackToReview,
}: ResultsPanelProps) {
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-50 p-6">
        <div className="text-center">
          <Loader2 className="w-10 h-10 lg:w-12 lg:h-12 text-primary-500 animate-spin mx-auto" />
          <p className="mt-3 lg:mt-4 text-sm lg:text-base text-slate-600">Running backtest...</p>
          <p className="mt-1 text-xs lg:text-sm text-slate-500">
            Compiling strategy and fetching data
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-50 p-4 lg:p-6">
        <div className="max-w-md text-center">
          <div className="w-12 h-12 lg:w-16 lg:h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <AlertCircle className="w-6 h-6 lg:w-8 lg:h-8 text-red-600" />
          </div>
          <h3 className="mt-3 lg:mt-4 text-base lg:text-lg font-semibold text-slate-800">
            Backtest Failed
          </h3>
          <p className="mt-2 text-sm text-slate-600 break-words">{error}</p>
        </div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-50 p-4">
        <div className="text-center">
          <div className="w-12 h-12 lg:w-16 lg:h-16 bg-slate-200 rounded-full flex items-center justify-center mx-auto">
            <BarChart3 className="w-6 h-6 lg:w-8 lg:h-8 text-slate-400" />
          </div>
          <h3 className="mt-3 lg:mt-4 text-base lg:text-lg font-semibold text-slate-600">
            No Results Yet
          </h3>
          <p className="mt-2 text-xs lg:text-sm text-slate-500 max-w-xs">
            Describe your trading strategy and click "Run Backtest" to see results here.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      {/* Header */}
      <div className="px-4 py-3 lg:px-6 lg:py-4 bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            {onBackToReview && (
              <button
                onClick={onBackToReview}
                className="p-1 text-slate-400 hover:text-slate-600 transition-colors flex-shrink-0"
                title="Back to script review"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
            )}
            <div className="min-w-0">
              <h2 className="text-base lg:text-lg font-semibold text-slate-800">
                Backtest Results
              </h2>
              <p className="text-xs lg:text-sm text-slate-500 truncate">
                Run ID: {result.run_id}
              </p>
            </div>
          </div>
          <div
            className={`px-2.5 py-1 lg:px-3 rounded-full text-xs lg:text-sm font-medium flex-shrink-0 ${
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

      <div className="p-4 lg:p-6 space-y-4 lg:space-y-6">
        {/* Strategy Info */}
        {strategySpec && <StrategyDisplay spec={strategySpec} />}

        {/* Script Code (for AI script proxy runs) */}
        {!strategySpec && generatedScript && scriptCode && (
          <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
            <div className="flex items-center gap-2 mb-2">
              <Code className="w-4 h-4 text-slate-500" />
              <h3 className="text-sm font-semibold text-slate-700">
                {generatedScript.strategy_name}
              </h3>
            </div>
            {generatedScript.strategy_description && (
              <p className="text-xs text-slate-500 mb-3">{generatedScript.strategy_description}</p>
            )}
            <pre className="text-xs bg-slate-50 rounded-lg p-3 overflow-x-auto max-h-48 overflow-y-auto">
              <code>{scriptCode}</code>
            </pre>
          </div>
        )}

        {/* Rating Panel (replaces flat metrics when available) */}
        {rating ? (
          <RatingPanel rating={rating} />
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-3 lg:gap-4">
            <MetricsCard
              label="Total Return"
              value={`${result.total_return >= 0 ? '+' : ''}${(
                result.total_return * 100
              ).toFixed(2)}%`}
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
              value={
                result.profit_factor === Infinity
                  ? 'N/A'
                  : result.profit_factor.toFixed(2)
              }
              variant={result.profit_factor >= 1.5 ? 'positive' : 'neutral'}
            />
          </div>
        )}

        {/* Equity Curve */}
        <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3 lg:mb-4">
            Equity Curve
          </h3>
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
