import { BacktestResult, StrategySpec } from '../hooks/useBacktest'
import { MetricsCard } from './MetricsCard'
import { EquityChart } from './EquityChart'
import { TradesTable } from './TradesTable'
import { StrategyDisplay } from './StrategyDisplay'
import { AlertCircle, Loader2, BarChart3 } from 'lucide-react'

interface ResultsPanelProps {
  result: BacktestResult | null
  strategySpec: StrategySpec | null
  isLoading: boolean
  error: string | null
}

export function ResultsPanel({
  result,
  strategySpec,
  isLoading,
  error,
}: ResultsPanelProps) {
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto" />
          <p className="mt-4 text-slate-600">Running backtest...</p>
          <p className="mt-1 text-sm text-slate-500">
            Compiling strategy and fetching data
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-50 p-6">
        <div className="max-w-md text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <AlertCircle className="w-8 h-8 text-red-600" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-slate-800">
            Backtest Failed
          </h3>
          <p className="mt-2 text-slate-600">{error}</p>
        </div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-16 h-16 bg-slate-200 rounded-full flex items-center justify-center mx-auto">
            <BarChart3 className="w-8 h-8 text-slate-400" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-slate-600">
            No Results Yet
          </h3>
          <p className="mt-2 text-sm text-slate-500 max-w-xs">
            Describe your trading strategy in the left panel and click
            "Run Backtest" to see results here.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      {/* Header */}
      <div className="px-6 py-4 bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-800">
              Backtest Results
            </h2>
            <p className="text-sm text-slate-500">
              Run ID: {result.run_id}
            </p>
          </div>
          <div
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              result.total_return >= 0
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-red-100 text-red-700'
            }`}
          >
            {result.total_return >= 0 ? '+' : ''}
            {(result.total_return * 100).toFixed(2)}% Return
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Strategy Info */}
        {strategySpec && <StrategyDisplay spec={strategySpec} />}

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
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

        {/* Equity Curve */}
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">
            Equity Curve
          </h3>
          <EquityChart data={result.equity_curve} />
        </div>

        {/* Trades Table */}
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">
            Trade History ({result.trades.length} trades)
          </h3>
          <TradesTable trades={result.trades} />
        </div>
      </div>
    </div>
  )
}
