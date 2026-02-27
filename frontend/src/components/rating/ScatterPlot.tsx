import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import { ChartContainer } from '../ChartContainer'

interface ScatterPlotProps {
  data: Array<{ x: number; y: number; label?: string }>
  xLabel: string
  yLabel: string
  color?: string
}

export function ScatterPlot({ data, xLabel, yLabel, color = '#6366f1' }: ScatterPlotProps) {
  if (!data.length) return <p className="text-xs text-slate-400">No data</p>

  return (
    <ChartContainer height={250}>
      <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="x"
          type="number"
          name={xLabel}
          tick={{ fontSize: 10 }}
          label={{ value: xLabel, position: 'bottom', fontSize: 11, fill: '#64748b' }}
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
        />
        <YAxis
          dataKey="y"
          type="number"
          name={yLabel}
          tick={{ fontSize: 10 }}
          label={{ value: yLabel, angle: -90, position: 'insideLeft', fontSize: 11, fill: '#64748b' }}
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
        />
        <Tooltip
          formatter={(value: number) => `${(value * 100).toFixed(2)}%`}
          labelFormatter={() => ''}
        />
        <Scatter data={data} fill={color} fillOpacity={0.6} r={4} />
      </ScatterChart>
    </ChartContainer>
  )
}
