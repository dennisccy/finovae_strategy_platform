import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { StrategyRating } from '../../hooks/useBacktest'
import { MetricsCard } from '../MetricsCard'
import { ChartContainer } from '../ChartContainer'

interface RiskRewardTabProps {
  rating: StrategyRating
}

export function RiskRewardTab({ rating }: RiskRewardTabProps) {
  const cat = rating.risk_reward
  const km = cat.key_metrics

  // Merge rolling sharpe data for chart
  const rollingSharpeData = mergeRollingSharpe(
    rating.rolling_sharpe,
    rating.rolling_sharpe_benchmark,
  )

  return (
    <div className="space-y-4">
      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
        <MetricsCard
          label="Sharpe Ratio"
          value={String(km.sharpe_ratio)}
          variant={Number(km.sharpe_ratio) >= 1 ? 'positive' : 'neutral'}
        />
        <MetricsCard
          label="Sortino Ratio"
          value={String(km.sortino_ratio)}
          variant={Number(km.sortino_ratio) >= 2 ? 'positive' : 'neutral'}
        />
        <MetricsCard
          label="Calmar Ratio"
          value={String(km.calmar_ratio)}
          variant={Number(km.calmar_ratio) >= 1 ? 'positive' : 'neutral'}
        />
        <MetricsCard
          label="Profit Factor"
          value={km.profit_factor === 'inf' ? '∞' : String(km.profit_factor)}
          variant={Number(km.profit_factor) >= 1.5 || km.profit_factor === 'inf' ? 'positive' : 'neutral'}
        />
        <MetricsCard
          label="Tail Ratio"
          value={String(km.tail_ratio)}
          variant={Number(km.tail_ratio) >= 1 ? 'positive' : 'neutral'}
        />
      </div>

      {/* Rolling Sharpe Chart */}
      {rollingSharpeData.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
          <h4 className="text-sm font-semibold text-slate-700 mb-3">
            Rolling Sharpe Ratio (90-period window)
          </h4>
          <ChartContainer height={250}>
            <LineChart data={rollingSharpeData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="time" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line
                type="monotone"
                dataKey="strategy"
                stroke="#10b981"
                dot={false}
                strokeWidth={1.5}
                name="Strategy"
              />
              <Line
                type="monotone"
                dataKey="benchmark"
                stroke="#94a3b8"
                dot={false}
                strokeWidth={1.5}
                name="Benchmark"
              />
            </LineChart>
          </ChartContainer>
        </div>
      )}
    </div>
  )
}

function mergeRollingSharpe(
  strategy: Array<{ timestamp: string; value: number }>,
  benchmark: Array<{ timestamp: string; value: number }>,
) {
  const bmMap = new Map(benchmark.map((b) => [b.timestamp, b.value]))
  const maxPoints = 200
  const step = Math.max(1, Math.floor(strategy.length / maxPoints))

  return strategy
    .filter((_, i) => i % step === 0)
    .map((s) => ({
      time: new Date(s.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
      strategy: Number(s.value.toFixed(2)),
      benchmark: Number((bmMap.get(s.timestamp) ?? 0).toFixed(2)),
    }))
}
