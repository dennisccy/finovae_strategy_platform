import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { ChartContainer } from '../ChartContainer'

interface BarComparisonProps {
  data: Array<{ label: string; long: number; short: number; benchmark: number }>
  longLabel?: string
  shortLabel?: string
  benchmarkLabel?: string
}

export function BarComparison({
  data,
  longLabel = 'Long',
  shortLabel = 'Short',
  benchmarkLabel = 'Benchmark',
}: BarComparisonProps) {
  if (!data.length) return <p className="text-xs text-slate-400">No data</p>

  return (
    <ChartContainer height={250}>
      <BarChart data={data} margin={{ top: 10, right: 10, bottom: 5, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="label" tick={{ fontSize: 10 }} />
        <YAxis
          tick={{ fontSize: 10 }}
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
        />
        <Tooltip formatter={(value: number) => `${(value * 100).toFixed(2)}%`} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Bar dataKey="long" name={longLabel} stackId="annual" fill="#3b82f6" radius={[0, 0, 0, 0]} />
        <Bar dataKey="short" name={shortLabel} stackId="annual" fill="#f59e0b" radius={[2, 2, 0, 0]} />
        <Bar dataKey="benchmark" name={benchmarkLabel} fill="#94a3b8" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ChartContainer>
  )
}
