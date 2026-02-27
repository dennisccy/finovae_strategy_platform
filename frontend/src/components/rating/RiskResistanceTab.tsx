import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import { StrategyRating } from '../../hooks/useBacktest'
import { MetricsCard } from '../MetricsCard'
import { ChartContainer } from '../ChartContainer'

interface RiskResistanceTabProps {
  rating: StrategyRating
}

export function RiskResistanceTab({ rating }: RiskResistanceTabProps) {
  const cat = rating.risk_resistance
  const km = cat.key_metrics

  // Top 5 drawdown periods table data
  const drawdowns = rating.drawdown_periods

  return (
    <div className="space-y-4">
      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
        <MetricsCard
          label="Max Drawdown"
          value={`-${km.max_drawdown}%`}
          variant="negative"
        />
        <MetricsCard
          label="Avg Drawdown"
          value={`-${km.avg_drawdown}%`}
          variant="negative"
        />
        <MetricsCard
          label="Avg Recovery"
          value={`${km.avg_recovery_days}d`}
          variant="neutral"
        />
        <MetricsCard
          label="VaR (5%)"
          value={`-${km.var_5}%`}
          variant="negative"
        />
        <MetricsCard
          label="CVaR (5%)"
          value={`-${km.cvar_5}%`}
          variant="negative"
        />
      </div>

      {/* Top 5 Drawdown Periods */}
      {drawdowns.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
          <h4 className="text-sm font-semibold text-slate-700 mb-3">
            Top {drawdowns.length} Worst Drawdowns
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 pr-2 font-medium text-slate-500">#</th>
                  <th className="text-left py-2 px-2 font-medium text-slate-500">Depth</th>
                  <th className="text-left py-2 px-2 font-medium text-slate-500">Start</th>
                  <th className="text-left py-2 px-2 font-medium text-slate-500">Duration</th>
                  <th className="text-left py-2 px-2 font-medium text-slate-500">Recovery</th>
                </tr>
              </thead>
              <tbody>
                {drawdowns.map((dd, i) => (
                  <tr key={i} className="border-b border-slate-100">
                    <td className="py-2 pr-2 text-slate-600">{i + 1}</td>
                    <td className="py-2 px-2 font-medium text-red-600">
                      -{(dd.depth * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 px-2 text-slate-600">
                      {new Date(dd.start_time).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </td>
                    <td className="py-2 px-2 text-slate-600">
                      {dd.duration_days.toFixed(0)}d
                    </td>
                    <td className="py-2 px-2 text-slate-600">
                      {dd.recovery_days !== null ? `${dd.recovery_days.toFixed(0)}d` : 'Ongoing'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Drawdown Chart */}
      {rating.benchmark_equity.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
          <h4 className="text-sm font-semibold text-slate-700 mb-3">Drawdown Over Time</h4>
          <DrawdownChart
            strategyEquity={[]}
            benchmarkEquity={rating.benchmark_equity}
          />
        </div>
      )}
    </div>
  )
}

function DrawdownChart({
  benchmarkEquity,
}: {
  strategyEquity: Array<{ timestamp: string; drawdown: number }>
  benchmarkEquity: Array<{ timestamp: string; drawdown: number }>
}) {
  // Sample data if too large
  const maxPoints = 300
  const step = Math.max(1, Math.floor(benchmarkEquity.length / maxPoints))
  const sampled = benchmarkEquity.filter((_, i) => i % step === 0)

  const chartData = sampled.map((ep) => ({
    time: new Date(ep.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
    benchmark: -(ep.drawdown * 100),
  }))

  return (
    <ChartContainer height={200}>
      <AreaChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="time" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 10 }} tickFormatter={(v: number) => `${v.toFixed(0)}%`} />
        <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
        <Area
          type="monotone"
          dataKey="benchmark"
          stroke="#94a3b8"
          fill="#e2e8f0"
          fillOpacity={0.5}
          name="Benchmark DD"
        />
      </AreaChart>
    </ChartContainer>
  )
}
