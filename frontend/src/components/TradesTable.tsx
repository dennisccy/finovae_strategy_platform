import { Trade } from '../hooks/useBacktest'
import { ArrowUpRight, ArrowDownRight } from 'lucide-react'

interface TradesTableProps {
  trades: Trade[]
}

export function TradesTable({ trades }: TradesTableProps) {
  if (!trades || trades.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        No trades executed
      </div>
    )
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatPrice = (price: number) => {
    if (price >= 1000) {
      return price.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    }
    return price.toFixed(4)
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500 border-b border-slate-200">
            <th className="pb-3 font-medium">#</th>
            <th className="pb-3 font-medium">Entry</th>
            <th className="pb-3 font-medium">Exit</th>
            <th className="pb-3 font-medium text-right">Entry Price</th>
            <th className="pb-3 font-medium text-right">Exit Price</th>
            <th className="pb-3 font-medium text-right">PnL</th>
            <th className="pb-3 font-medium text-right">Return</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {trades.slice(0, 50).map((trade, index) => (
            <tr key={trade.trade_id} className="hover:bg-slate-50">
              <td className="py-3 text-slate-600">{index + 1}</td>
              <td className="py-3 text-slate-600">{formatDate(trade.entry_time)}</td>
              <td className="py-3 text-slate-600">{formatDate(trade.exit_time)}</td>
              <td className="py-3 text-right text-slate-800 font-mono">
                ${formatPrice(trade.entry_price)}
              </td>
              <td className="py-3 text-right text-slate-800 font-mono">
                ${formatPrice(trade.exit_price)}
              </td>
              <td
                className={`py-3 text-right font-medium font-mono ${
                  trade.pnl >= 0 ? 'text-emerald-600' : 'text-red-600'
                }`}
              >
                {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
              </td>
              <td className="py-3 text-right">
                <span
                  className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                    trade.pnl_percent >= 0
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-red-100 text-red-700'
                  }`}
                >
                  {trade.pnl_percent >= 0 ? (
                    <ArrowUpRight className="w-3 h-3" />
                  ) : (
                    <ArrowDownRight className="w-3 h-3" />
                  )}
                  {trade.pnl_percent >= 0 ? '+' : ''}
                  {(trade.pnl_percent * 100).toFixed(2)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {trades.length > 50 && (
        <p className="text-center text-sm text-slate-500 mt-4">
          Showing first 50 of {trades.length} trades
        </p>
      )}
    </div>
  )
}
