import { BacktestResult, StrategyRating } from '../hooks/useBacktest'
import { MetricsCard } from './MetricsCard'
import { EquityChart } from './EquityChart'
import { TradesTable } from './TradesTable'
import { RatingPanel } from './RatingPanel'

interface ResultsPanelProps {
  result: BacktestResult
  rating: StrategyRating | null
}

export function ResultsPanel({ result, rating }: ResultsPanelProps) {
  return (
    <div className="space-y-4 lg:space-y-6">
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
  )
}
