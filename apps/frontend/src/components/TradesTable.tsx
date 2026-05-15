import { useState, useMemo } from 'react'
import { Trade } from '../hooks/useBacktest'
import {
  ArrowUpRight,
  ArrowDownRight,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
} from 'lucide-react'

type SortKey = 'entry_time' | 'exit_time' | 'pnl' | 'pnl_percent'
type SortDir = 'asc' | 'desc'
type DirFilter = 'all' | 'long' | 'short'

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100]

interface TradesTableProps {
  trades: Trade[]
}

function SortIcon({ col, sortKey, sortDir }: { col: SortKey; sortKey: SortKey; sortDir: SortDir }) {
  if (col !== sortKey) return <ChevronsUpDown className="w-3 h-3 inline ml-0.5 opacity-30" />
  return sortDir === 'asc'
    ? <ChevronUp className="w-3 h-3 inline ml-0.5 text-primary-600" />
    : <ChevronDown className="w-3 h-3 inline ml-0.5 text-primary-600" />
}

export function TradesTable({ trades }: TradesTableProps) {
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(25)
  const [filterYear, setFilterYear] = useState<number | null>(null)
  const [filterDir, setFilterDir] = useState<DirFilter>('all')
  const [sortKey, setSortKey] = useState<SortKey>('entry_time')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const years = useMemo(() => {
    const s = new Set((trades ?? []).map(t => new Date(t.entry_time).getFullYear()))
    return [...s].sort((a, b) => a - b)
  }, [trades])

  const processedTrades = useMemo(() => {
    let result = [...(trades ?? [])]
    if (filterYear !== null) {
      result = result.filter(t => new Date(t.entry_time).getFullYear() === filterYear)
    }
    if (filterDir !== 'all') {
      result = result.filter(t => (t.direction ?? 'long') === filterDir)
    }
    result.sort((a, b) => {
      let av: number, bv: number
      if (sortKey === 'entry_time') {
        av = new Date(a.entry_time).getTime()
        bv = new Date(b.entry_time).getTime()
      } else if (sortKey === 'exit_time') {
        av = new Date(a.exit_time).getTime()
        bv = new Date(b.exit_time).getTime()
      } else {
        av = a[sortKey]
        bv = b[sortKey]
      }
      return sortDir === 'asc' ? av - bv : bv - av
    })
    return result
  }, [trades, filterYear, filterDir, sortKey, sortDir])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
    setPage(0)
  }

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

  const totalPages = Math.ceil(processedTrades.length / pageSize)
  const safePage = Math.min(page, Math.max(0, totalPages - 1))
  const pageTrades = processedTrades.slice(safePage * pageSize, (safePage + 1) * pageSize)
  const globalOffset = safePage * pageSize

  const hasLong = trades.some(t => (t.direction ?? 'long') === 'long')
  const hasShort = trades.some(t => t.direction === 'short')
  const showDirFilter = hasLong && hasShort

  function Pagination() {
    return (
      <div className="flex flex-wrap items-center justify-between gap-2 mt-3 pt-3 border-t border-slate-100">
        <span className="text-xs text-slate-500">
          {processedTrades.length === 0
            ? '0 trades'
            : `${globalOffset + 1}–${Math.min(globalOffset + pageSize, processedTrades.length)} of ${processedTrades.length}`}
          {processedTrades.length !== trades.length && (
            <span className="text-slate-400"> (filtered from {trades.length})</span>
          )}
        </span>
        <div className="flex items-center gap-2">
          {totalPages > 1 && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(0)}
                disabled={safePage === 0}
                className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="First page"
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={safePage === 0}
                className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Previous page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <select
                value={safePage}
                onChange={e => setPage(Number(e.target.value))}
                className="text-xs text-slate-700 bg-white border border-slate-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary-500 cursor-pointer"
              >
                {Array.from({ length: totalPages }, (_, i) => (
                  <option key={i} value={i}>Page {i + 1} of {totalPages}</option>
                ))}
              </select>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={safePage === totalPages - 1}
                className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Next page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(totalPages - 1)}
                disabled={safePage === totalPages - 1}
                className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Last page"
              >
                <ChevronsRight className="w-4 h-4" />
              </button>
            </div>
          )}
          <select
            value={pageSize}
            onChange={e => { setPageSize(Number(e.target.value)); setPage(0) }}
            className="text-xs text-slate-700 bg-white border border-slate-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary-500 cursor-pointer"
            title="Rows per page"
          >
            {PAGE_SIZE_OPTIONS.map(n => (
              <option key={n} value={n}>{n} per page</option>
            ))}
          </select>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {/* Year filter */}
        {years.length > 1 && (
          <select
            value={filterYear ?? ''}
            onChange={e => { setFilterYear(e.target.value === '' ? null : Number(e.target.value)); setPage(0) }}
            className="text-xs text-slate-700 bg-white border border-slate-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary-500 cursor-pointer"
          >
            <option value="">All Years</option>
            {years.map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        )}

        {/* Direction filter */}
        {showDirFilter && (
          <div className="flex items-center rounded-lg border border-slate-200 overflow-hidden text-xs">
            {(['all', 'long', 'short'] as DirFilter[]).map(d => (
              <button
                key={d}
                onClick={() => { setFilterDir(d); setPage(0) }}
                className={`px-2.5 py-1 font-medium transition-colors ${
                  filterDir === d
                    ? d === 'long'
                      ? 'bg-blue-100 text-blue-700'
                      : d === 'short'
                      ? 'bg-orange-100 text-orange-700'
                      : 'bg-slate-100 text-slate-700'
                    : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'
                }`}
              >
                {d === 'all' ? 'All' : d === 'long' ? 'Long' : 'Short'}
              </button>
            ))}
          </div>
        )}

        {/* Result count */}
        {processedTrades.length !== trades.length && (
          <span className="text-xs text-slate-400">
            {processedTrades.length} of {trades.length} trades
          </span>
        )}
      </div>

      {processedTrades.length === 0 ? (
        <div className="text-center py-6 text-sm text-slate-400">No trades match filters</div>
      ) : (
        <>
          {/* Mobile card layout */}
          <div className="md:hidden space-y-2">
            {pageTrades.map((trade, index) => (
              <div key={trade.trade_id} className="border border-slate-100 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-slate-500">#{globalOffset + index + 1}</span>
                    <span
                      className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold ${
                        trade.direction === 'short'
                          ? 'bg-orange-100 text-orange-700'
                          : 'bg-blue-100 text-blue-700'
                      }`}
                    >
                      {trade.direction === 'short' ? 'S' : 'L'}
                    </span>
                  </div>
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
            {Pagination()}
          </div>

          {/* Desktop table layout */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-slate-200">
                  <th className="pb-3 font-medium">#</th>
                  <th className="pb-3 font-medium">Dir</th>
                  <th
                    className="pb-3 font-medium cursor-pointer hover:text-slate-700 select-none"
                    onClick={() => handleSort('entry_time')}
                  >
                    Entry <SortIcon col="entry_time" sortKey={sortKey} sortDir={sortDir} />
                  </th>
                  <th
                    className="pb-3 font-medium cursor-pointer hover:text-slate-700 select-none"
                    onClick={() => handleSort('exit_time')}
                  >
                    Exit <SortIcon col="exit_time" sortKey={sortKey} sortDir={sortDir} />
                  </th>
                  <th className="pb-3 font-medium text-right">Entry Price</th>
                  <th className="pb-3 font-medium text-right">Exit Price</th>
                  <th
                    className="pb-3 font-medium text-right cursor-pointer hover:text-slate-700 select-none"
                    onClick={() => handleSort('pnl')}
                  >
                    PnL <SortIcon col="pnl" sortKey={sortKey} sortDir={sortDir} />
                  </th>
                  <th
                    className="pb-3 font-medium text-right cursor-pointer hover:text-slate-700 select-none"
                    onClick={() => handleSort('pnl_percent')}
                  >
                    Return <SortIcon col="pnl_percent" sortKey={sortKey} sortDir={sortDir} />
                  </th>
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
                  )
                })}
              </tbody>
            </table>
            {Pagination()}
          </div>
        </>
      )}
    </>
  )
}
