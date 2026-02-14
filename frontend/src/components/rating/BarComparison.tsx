import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface BarComparisonProps {
  data: Array<{ label: string; strategy: number; benchmark: number }>
  strategyLabel?: string
  benchmarkLabel?: string
}

export function BarComparison({
  data,
  strategyLabel = 'Strategy',
  benchmarkLabel = 'Benchmark',
}: BarComparisonProps) {
  if (!data.length) return <p className="text-xs text-slate-400">No data</p>

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data} margin={{ top: 10, right: 10, bottom: 5, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="label" tick={{ fontSize: 10 }} />
        <YAxis
          tick={{ fontSize: 10 }}
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
        />
        <Tooltip formatter={(value: number) => `${(value * 100).toFixed(2)}%`} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Bar dataKey="strategy" name={strategyLabel} fill="#10b981" radius={[2, 2, 0, 0]} />
        <Bar dataKey="benchmark" name={benchmarkLabel} fill="#94a3b8" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
