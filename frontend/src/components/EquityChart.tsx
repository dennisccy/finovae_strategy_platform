import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import { EquityPoint } from '../hooks/useBacktest'

interface EquityChartProps {
  data: EquityPoint[]
}

export function EquityChart({ data }: EquityChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-48 lg:h-64 flex items-center justify-center text-sm text-slate-500">
        No equity data available
      </div>
    )
  }

  // Sample data if too many points (for performance)
  const sampledData =
    data.length > 500
      ? data.filter((_, i) => i % Math.ceil(data.length / 500) === 0)
      : data

  const chartData = sampledData.map((point) => ({
    timestamp: new Date(point.timestamp).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    }),
    equity: point.equity,
    drawdown: point.drawdown * 100,
  }))

  const formatValue = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`
    }
    if (value >= 1000) {
      return `$${(value / 1000).toFixed(1)}K`
    }
    return `$${value.toFixed(0)}`
  }

  return (
    <div className="h-48 sm:h-56 lg:h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="timestamp"
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
            tickFormatter={formatValue}
            width={52}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              fontSize: '12px',
            }}
            formatter={(value: number, name: string) => [
              name === 'equity' ? formatValue(value) : `${value.toFixed(2)}%`,
              name === 'equity' ? 'Equity' : 'Drawdown',
            ]}
            labelStyle={{ color: '#64748b', fontSize: '12px' }}
          />
          <Area
            type="monotone"
            dataKey="equity"
            stroke="#0ea5e9"
            strokeWidth={2}
            fill="url(#equityGradient)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
