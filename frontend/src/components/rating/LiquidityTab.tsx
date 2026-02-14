import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { StrategyRating } from '../../hooks/useBacktest'
import { MetricsCard } from '../MetricsCard'

interface LiquidityTabProps {
  rating: StrategyRating
}

function formatUSDT(val: number): string {
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`
  return `$${val.toFixed(0)}`
}

export function LiquidityTab({ rating }: LiquidityTabProps) {
  const cat = rating.liquidity
  const km = cat.key_metrics

  // Capacity chart data
  const capacityData = rating.capacity_levels.map((cl) => ({
    capital: formatUSDT(cl.capital),
    vpr: cl.volume_participation_pct,
    slippage: cl.estimated_slippage_bps,
  }))

  return (
    <div className="space-y-4">
      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
        <MetricsCard
          label="Avg Daily Volume"
          value={formatUSDT(Number(km.avg_daily_volume))}
          variant="neutral"
        />
        <MetricsCard
          label="Volume Participation"
          value={`${km.volume_participation_rate}%`}
          variant={Number(km.volume_participation_rate) < 5 ? 'positive' : 'negative'}
        />
        <MetricsCard
          label="Est. Capacity"
          value={formatUSDT(Number(km.estimated_capacity))}
          variant={Number(km.estimated_capacity) >= 100000 ? 'positive' : 'neutral'}
        />
        <MetricsCard
          label="Spread Impact"
          value={`${km.avg_spread_impact}%`}
          variant="neutral"
        />
        <MetricsCard
          label="Entry/Exit Vol Ratio"
          value={String(km.entry_exit_volume_ratio)}
          variant="neutral"
        />
      </div>

      {/* Capacity Analysis */}
      {capacityData.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
          <h4 className="text-sm font-semibold text-slate-700 mb-3">
            Capacity Analysis — Volume Participation at Different Capital Levels
          </h4>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={capacityData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="capital" tick={{ fontSize: 10 }} />
              <YAxis
                yAxisId="vpr"
                tick={{ fontSize: 10 }}
                tickFormatter={(v: number) => `${v.toFixed(1)}%`}
                label={{ value: 'VPR %', angle: -90, position: 'insideLeft', fontSize: 10, fill: '#64748b' }}
              />
              <YAxis
                yAxisId="slip"
                orientation="right"
                tick={{ fontSize: 10 }}
                tickFormatter={(v: number) => `${v.toFixed(0)}bps`}
                label={{ value: 'Slippage', angle: 90, position: 'insideRight', fontSize: 10, fill: '#64748b' }}
              />
              <Tooltip />
              <Bar yAxisId="vpr" dataKey="vpr" name="Vol Participation %" fill="#06b6d4" radius={[2, 2, 0, 0]} />
              <Bar yAxisId="slip" dataKey="slippage" name="Est. Slippage (bps)" fill="#f59e0b" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
