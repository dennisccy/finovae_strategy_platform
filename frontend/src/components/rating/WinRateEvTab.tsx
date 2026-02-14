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
import { ScatterPlot } from './ScatterPlot'

interface WinRateEvTabProps {
  rating: StrategyRating
}

export function WinRateEvTab({ rating }: WinRateEvTabProps) {
  const cat = rating.win_rate_ev
  const km = cat.key_metrics

  // Histogram data
  const histData = rating.return_distribution.map((bin) => ({
    range: `${(bin.bin_start * 100).toFixed(0)}%`,
    count: bin.count,
    fill: bin.bin_start >= 0 ? '#10b981' : '#ef4444',
  }))

  // MAE vs Return scatter data
  const maeReturnData = rating.trade_excursions.map((te) => ({
    x: te.mae,
    y: te.pnl_percent,
    label: te.trade_id,
  }))

  // MFE vs Return scatter data
  const mfeReturnData = rating.trade_excursions.map((te) => ({
    x: te.mfe,
    y: te.pnl_percent,
    label: te.trade_id,
  }))

  // MAE vs MFE scatter data
  const maeMfeData = rating.trade_excursions.map((te) => ({
    x: te.mae,
    y: te.mfe,
    label: te.trade_id,
  }))

  // Simulated stop-loss data
  const stopData = rating.simulated_stops.map((s) => ({
    level: `${s.level_pct}%`,
    return: s.adjusted_return,
    win_rate: s.adjusted_win_rate,
    affected: s.trades_affected,
  }))

  // Simulated take-profit data
  const tpData = rating.simulated_take_profits.map((s) => ({
    level: `${s.level_pct}%`,
    return: s.adjusted_return,
    win_rate: s.adjusted_win_rate,
    affected: s.trades_affected,
  }))

  return (
    <div className="space-y-4">
      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
        <MetricsCard
          label="Win Rate"
          value={`${km.win_rate}%`}
          variant={Number(km.win_rate) >= 50 ? 'positive' : 'neutral'}
        />
        <MetricsCard
          label="Beat BM Monthly"
          value={`${km.monthly_beat_rate}%`}
          variant={Number(km.monthly_beat_rate) >= 50 ? 'positive' : 'neutral'}
        />
        <MetricsCard
          label="Expected Value"
          value={`${Number(km.expected_value) >= 0 ? '+' : ''}${km.expected_value}%`}
          variant={Number(km.expected_value) >= 0 ? 'positive' : 'negative'}
        />
        <MetricsCard
          label="Avg MAE"
          value={`-${km.avg_mae}%`}
          variant="negative"
        />
        <MetricsCard
          label="Avg MFE"
          value={`+${km.avg_mfe}%`}
          variant="positive"
        />
      </div>

      {/* Return Distribution Histogram */}
      {histData.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
          <h4 className="text-sm font-semibold text-slate-700 mb-3">
            Trade Return Distribution
          </h4>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={histData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="range" tick={{ fontSize: 9 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="count" name="Trades" radius={[2, 2, 0, 0]}>
                {histData.map((entry, index) => (
                  <rect key={index} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Simulated Stop-Loss / Take-Profit */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {stopData.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
            <h4 className="text-sm font-semibold text-slate-700 mb-3">
              Simulated Stop-Loss
            </h4>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-1 font-medium text-slate-500">Level</th>
                    <th className="text-right py-1 font-medium text-slate-500">Return</th>
                    <th className="text-right py-1 font-medium text-slate-500">Win%</th>
                    <th className="text-right py-1 font-medium text-slate-500">Hit</th>
                  </tr>
                </thead>
                <tbody>
                  {stopData.map((row, i) => (
                    <tr key={i} className="border-b border-slate-50">
                      <td className="py-1 text-slate-600">{row.level}</td>
                      <td className={`py-1 text-right ${row.return >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {row.return >= 0 ? '+' : ''}{row.return.toFixed(1)}%
                      </td>
                      <td className="py-1 text-right text-slate-600">{row.win_rate}%</td>
                      <td className="py-1 text-right text-slate-500">{row.affected}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tpData.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
            <h4 className="text-sm font-semibold text-slate-700 mb-3">
              Simulated Take-Profit
            </h4>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-1 font-medium text-slate-500">Level</th>
                    <th className="text-right py-1 font-medium text-slate-500">Return</th>
                    <th className="text-right py-1 font-medium text-slate-500">Win%</th>
                    <th className="text-right py-1 font-medium text-slate-500">Hit</th>
                  </tr>
                </thead>
                <tbody>
                  {tpData.map((row, i) => (
                    <tr key={i} className="border-b border-slate-50">
                      <td className="py-1 text-slate-600">{row.level}</td>
                      <td className={`py-1 text-right ${row.return >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {row.return >= 0 ? '+' : ''}{row.return.toFixed(1)}%
                      </td>
                      <td className="py-1 text-right text-slate-600">{row.win_rate}%</td>
                      <td className="py-1 text-right text-slate-500">{row.affected}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* MAE/MFE Scatter Plots */}
      {maeReturnData.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
            <h4 className="text-sm font-semibold text-slate-700 mb-3">Return vs MAE</h4>
            <ScatterPlot data={maeReturnData} xLabel="MAE" yLabel="Return" color="#ef4444" />
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
            <h4 className="text-sm font-semibold text-slate-700 mb-3">Return vs MFE</h4>
            <ScatterPlot data={mfeReturnData} xLabel="MFE" yLabel="Return" color="#10b981" />
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
            <h4 className="text-sm font-semibold text-slate-700 mb-3">MAE vs MFE</h4>
            <ScatterPlot data={maeMfeData} xLabel="MAE" yLabel="MFE" color="#6366f1" />
          </div>
        </div>
      )}
    </div>
  )
}
