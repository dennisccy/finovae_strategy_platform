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

  // Annual returns comparison data — long + short stacked, benchmark separate
  const allYears = new Set([
    ...Object.keys(rating.annual_long_returns ?? {}).map(Number),
    ...Object.keys(rating.annual_short_returns ?? {}).map(Number),
    ...Object.keys(rating.benchmark_annual_returns).map(Number),
  ])
  const annualData = [...allYears]
    .sort()
    .map((year) => ({
      label: String(year),
      long: rating.annual_long_returns?.[year] || 0,
      short: rating.annual_short_returns?.[year] || 0,
      benchmark: rating.benchmark_annual_returns[year] || 0,
    }))

  return (
    <div className="space-y-4">
      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
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
        <MetricsCard
          label="Total Commissions"
          value={`$${Number(km.total_commission).toFixed(2)}`}
          variant="negative"
        />
        <MetricsCard
          label="Fee Drag"
          value={`-${km.commission_pct_capital}%`}
          variant="negative"
        />
        <MetricsCard
          label="Return from Long"
          value={`${Number(km.return_from_long) >= 0 ? '+' : ''}${km.return_from_long ?? '—'}%`}
          variant={Number(km.return_from_long) >= 0 ? 'positive' : 'negative'}
        />
        <MetricsCard
          label="Return from Short"
          value={`${Number(km.return_from_short) >= 0 ? '+' : ''}${km.return_from_short ?? '—'}%`}
          variant={Number(km.return_from_short) >= 0 ? 'positive' : 'negative'}
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
