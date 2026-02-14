import { StrategyRating } from '../../hooks/useBacktest'
import { MetricsCard } from '../MetricsCard'
import { EquityChart } from '../EquityChart'
import { MonthlyHeatmap } from './MonthlyHeatmap'
import { BarComparison } from './BarComparison'

interface ProfitabilityTabProps {
  rating: StrategyRating
}

export function ProfitabilityTab({ rating }: ProfitabilityTabProps) {
  const cat = rating.profitability
  const km = cat.key_metrics

  // Annual returns comparison data
  const annualData = Object.keys(rating.annual_returns)
    .map(Number)
    .sort()
    .map((year) => ({
      label: String(year),
      strategy: rating.annual_returns[year] || 0,
      benchmark: rating.benchmark_annual_returns[year] || 0,
    }))

  return (
    <div className="space-y-4">
      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
        <MetricsCard
          label="Annual Return"
          value={`${Number(km.annual_return) >= 0 ? '+' : ''}${km.annual_return}%`}
          variant={Number(km.annual_return) >= 0 ? 'positive' : 'negative'}
        />
        <MetricsCard
          label="Alpha"
          value={`${Number(km.alpha) >= 0 ? '+' : ''}${km.alpha}%`}
          variant={Number(km.alpha) >= 0 ? 'positive' : 'negative'}
        />
        <MetricsCard
          label="Beta"
          value={String(km.beta)}
          variant="neutral"
        />
        <MetricsCard
          label="Avg Duration"
          value={`${km.avg_trade_duration_days}d`}
          variant="neutral"
        />
        <MetricsCard
          label="Total Trades"
          value={String(km.total_trades)}
          variant="neutral"
        />
      </div>

      {/* Monthly Returns Heatmap */}
      <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
        <h4 className="text-sm font-semibold text-slate-700 mb-3">Monthly Returns</h4>
        <MonthlyHeatmap data={rating.monthly_returns} />
      </div>

      {/* Annual Returns vs Benchmark */}
      {annualData.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
          <h4 className="text-sm font-semibold text-slate-700 mb-3">
            Annual Returns vs Benchmark
          </h4>
          <BarComparison data={annualData} />
        </div>
      )}

      {/* Benchmark Equity Curve */}
      {rating.benchmark_equity.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
          <h4 className="text-sm font-semibold text-slate-700 mb-3">
            Benchmark (Buy & Hold) — {(rating.benchmark_total_return * 100).toFixed(2)}%
          </h4>
          <EquityChart data={rating.benchmark_equity} />
        </div>
      )}
    </div>
  )
}
