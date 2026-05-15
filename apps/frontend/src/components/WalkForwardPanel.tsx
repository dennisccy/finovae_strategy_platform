import type { WalkForwardResult } from '../hooks/useBacktest'
import { EquityChart } from './EquityChart'

interface WalkForwardPanelProps {
  result: WalkForwardResult
}

function pct(v: number, decimals = 2) {
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(decimals)}%`
}

function WfeBadge({ wfe }: { wfe: number }) {
  const label = wfe.toFixed(2)
  if (wfe >= 0.5) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700">
        WFE {label} ✓
      </span>
    )
  }
  if (wfe >= 0.3) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-700">
        WFE {label} ~
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700">
      WFE {label} ✗
    </span>
  )
}

function MetricCell({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  const color =
    positive === undefined
      ? 'text-slate-700'
      : positive
      ? 'text-emerald-600'
      : 'text-red-600'
  return (
    <div className="text-center">
      <p className="text-xs text-slate-400 mb-0.5">{label}</p>
      <p className={`text-sm font-semibold ${color}`}>{value}</p>
    </div>
  )
}

export function WalkForwardPanel({ result }: WalkForwardPanelProps) {
  if (!result || result.num_windows === 0) {
    return (
      <div className="text-sm text-slate-500 text-center py-4">
        No windows completed.
        {result?.errors?.length > 0 && (
          <p className="text-xs text-red-500 mt-1">{result.errors[0]}</p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Non-critical errors */}
      {result.errors.length > 0 && (
        <div className="px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
          {result.errors.length} window(s) skipped — {result.errors[0]}
          {result.errors.length > 1 && ` (+${result.errors.length - 1} more)`}
        </div>
      )}

      {/* Aggregate metrics row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
        <MetricCell
          label="OOS Return"
          value={pct(result.combined_oos_return)}
          positive={result.combined_oos_return >= 0}
        />
        <MetricCell
          label="OOS Sharpe"
          value={result.combined_oos_sharpe.toFixed(2)}
          positive={result.combined_oos_sharpe >= 1}
        />
        <MetricCell
          label="OOS Win Rate"
          value={`${(result.combined_oos_win_rate * 100).toFixed(1)}%`}
          positive={result.combined_oos_win_rate >= 0.5}
        />
        <MetricCell
          label="OOS Max DD"
          value={`-${(result.combined_oos_max_drawdown * 100).toFixed(2)}%`}
          positive={false}
        />
        <div className="text-center">
          <p className="text-xs text-slate-400 mb-0.5">Walk-Forward Eff.</p>
          <WfeBadge wfe={result.wfe} />
        </div>
      </div>

      {/* Per-window table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="px-3 py-2 text-left font-medium text-slate-500">#</th>
                <th className="px-3 py-2 text-left font-medium text-slate-500">IS Period</th>
                <th className="px-3 py-2 text-left font-medium text-slate-500">OOS Period</th>
                <th className="px-3 py-2 text-right font-medium text-slate-500">IS Return</th>
                <th className="px-3 py-2 text-right font-medium text-slate-500">OOS Return</th>
                <th className="px-3 py-2 text-right font-medium text-slate-500">IS Sharpe</th>
                <th className="px-3 py-2 text-right font-medium text-slate-500">OOS Sharpe</th>
                <th className="px-3 py-2 text-right font-medium text-slate-500">IS Trades</th>
                <th className="px-3 py-2 text-right font-medium text-slate-500">OOS Trades</th>
              </tr>
            </thead>
            <tbody>
              {result.windows.map(w => (
                <tr
                  key={w.window_index}
                  className={`border-b border-slate-100 last:border-0 ${
                    w.oos_total_return >= 0 ? 'bg-white' : 'bg-red-50/40'
                  }`}
                >
                  <td className="px-3 py-2 text-slate-500">{w.window_index}</td>
                  <td className="px-3 py-2 text-slate-600 whitespace-nowrap">
                    {w.is_start} – {w.is_end}
                  </td>
                  <td className="px-3 py-2 text-slate-600 whitespace-nowrap">
                    {w.oos_start} – {w.oos_end}
                  </td>
                  <td className={`px-3 py-2 text-right font-medium ${w.is_total_return >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                    {pct(w.is_total_return)}
                  </td>
                  <td className={`px-3 py-2 text-right font-medium ${w.oos_total_return >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                    {pct(w.oos_total_return)}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-600">{w.is_sharpe.toFixed(2)}</td>
                  <td className="px-3 py-2 text-right text-slate-600">{w.oos_sharpe.toFixed(2)}</td>
                  <td className="px-3 py-2 text-right text-slate-500">{w.is_num_trades}</td>
                  <td className="px-3 py-2 text-right text-slate-500">{w.oos_num_trades}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Combined OOS equity curve */}
      {result.combined_oos_equity.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
          <h4 className="text-xs font-semibold text-slate-600 mb-3">
            Combined OOS Equity Curve ({result.num_windows} windows chained)
          </h4>
          <EquityChart data={result.combined_oos_equity} />
        </div>
      )}
    </div>
  )
}
