import { useState } from 'react'
import { Trade } from '../hooks/useBacktest'
import { ArrowUpRight, ArrowDownRight, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

interface TradesTableProps {
  trades: Trade[]
}

const PAGE_SIZE = 25

export function TradesTable({ trades }: TradesTableProps) {
  const [page, setPage] = useState(0)

  if (!trades || trades.length === 0) {
    return (
      <div className="text-center py-6 lg:py-8 text-sm text-slate-500">
        No trades executed
      </div>
    )
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatDateShort = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
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

  const sortedTrades = [...trades].sort((a, b) =>
    new Date(b.entry_time).getTime() - new Date(a.entry_time).getTime()
  )

  const totalPages = Math.ceil(sortedTrades.length / PAGE_SIZE)
  const pageTrades = sortedTrades.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const globalOffset = page * PAGE_SIZE

  function Pagination() {
    if (totalPages <= 1) return null
    return (
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100">
        <span className="text-xs text-slate-500">
          {globalOffset + 1}–{Math.min(globalOffset + PAGE_SIZE, sortedTrades.length)} of {sortedTrades.length}
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPage(0)}
            disabled={page === 0}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="First page"
          >
            <ChevronsLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => setPage(p => p - 1)}
            disabled={page === 0}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Previous page"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <select
            value={page}
            onChange={e => setPage(Number(e.target.value))}
            className="text-xs text-slate-700 bg-white border border-slate-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary-500 cursor-pointer"
          >
            {Array.from({ length: totalPages }, (_, i) => (
              <option key={i} value={i}>Page {i + 1} of {totalPages}</option>
            ))}
          </select>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page === totalPages - 1}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Next page"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <button
            onClick={() => setPage(totalPages - 1)}
            disabled={page === totalPages - 1}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Last page"
          >
            <ChevronsRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Mobile card layout */}
      <div className="md:hidden space-y-2">
        {pageTrades.map((trade, index) => (
          <div key={trade.trade_id} className="border border-slate-100 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-500">#{globalOffset + index + 1}</span>
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
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
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <div>
                <span className="text-slate-400">Entry</span>
                <p className="text-slate-700 font-mono">${formatPrice(trade.entry_price)}</p>
                <p className="text-slate-500">{formatDateShort(trade.entry_time)}</p>
              </div>
              <div>
                <span className="text-slate-400">Exit</span>
                <p className="text-slate-700 font-mono">${formatPrice(trade.exit_price)}</p>
                <p className="text-slate-500">{formatDateShort(trade.exit_time)}</p>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-slate-50 text-xs">
              <span className="text-slate-400">PnL: </span>
              <span className={`font-medium font-mono ${trade.pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
              </span>
            </div>
          </div>
        ))}
        <Pagination />
      </div>

      {/* Desktop table layout */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b border-slate-200">
              <th className="pb-3 font-medium">#</th>
              <th className="pb-3 font-medium">Dir</th>
              <th className="pb-3 font-medium">Entry</th>
              <th className="pb-3 font-medium">Exit</th>
              <th className="pb-3 font-medium text-right">Entry Price</th>
              <th className="pb-3 font-medium text-right">Exit Price</th>
              <th className="pb-3 font-medium text-right">PnL</th>
              <th className="pb-3 font-medium text-right">Return</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {pageTrades.map((trade, index) => {
              const isShort = trade.direction === 'short'
              const lev = trade.leverage && trade.leverage > 1 ? trade.leverage : null
              return (
              <tr key={trade.trade_id} className="hover:bg-slate-50">
                <td className="py-3 text-slate-600">{globalOffset + index + 1}</td>
                <td className="py-3">
                  <span
                    className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold ${
                      isShort
                        ? 'bg-orange-100 text-orange-700'
                        : 'bg-blue-100 text-blue-700'
                    }`}
                  >
                    {isShort ? 'S' : 'L'}{lev ? ` ${lev}x` : ''}
                  </span>
                </td>
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
            )})}

          </tbody>
        </table>
        <Pagination />
      </div>
    </>
  )
}
