import { MonthlyReturn } from '../../hooks/useBacktest'

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

interface MonthlyHeatmapProps {
  data: MonthlyReturn[]
}

function getColor(value: number): string {
  if (value > 0.10) return 'bg-emerald-600 text-white'
  if (value > 0.05) return 'bg-emerald-500 text-white'
  if (value > 0.02) return 'bg-emerald-400 text-white'
  if (value > 0) return 'bg-emerald-200 text-emerald-800'
  if (value === 0) return 'bg-slate-100 text-slate-500'
  if (value > -0.02) return 'bg-red-200 text-red-800'
  if (value > -0.05) return 'bg-red-400 text-white'
  if (value > -0.10) return 'bg-red-500 text-white'
  return 'bg-red-600 text-white'
}

export function MonthlyHeatmap({ data }: MonthlyHeatmapProps) {
  if (!data.length) return <p className="text-xs text-slate-400">No monthly data</p>

  // Group by year
  const byYear: Record<number, Record<number, number>> = {}
  for (const mr of data) {
    if (!byYear[mr.year]) byYear[mr.year] = {}
    byYear[mr.year][mr.month] = mr.return_pct
  }

  const years = Object.keys(byYear).map(Number).sort()

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="text-left py-1 pr-2 text-slate-500 font-medium">Year</th>
            {MONTH_LABELS.map((m) => (
              <th key={m} className="py-1 px-1 text-center text-slate-500 font-medium">
                {m}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {years.map((year) => (
            <tr key={year}>
              <td className="py-1 pr-2 font-medium text-slate-600">{year}</td>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => {
                const val = byYear[year]?.[month]
                if (val === undefined) {
                  return <td key={month} className="py-1 px-1"><div className="w-full h-6 rounded bg-slate-50" /></td>
                }
                return (
                  <td key={month} className="py-1 px-1">
                    <div
                      className={`w-full h-6 rounded flex items-center justify-center text-[10px] font-medium ${getColor(val)}`}
                      title={`${year}-${String(month).padStart(2, '0')}: ${(val * 100).toFixed(1)}%`}
                    >
                      {(val * 100).toFixed(1)}
                    </div>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
