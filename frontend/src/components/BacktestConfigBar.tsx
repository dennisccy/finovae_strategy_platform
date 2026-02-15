import { RotateCw } from 'lucide-react'
import type { BacktestParams } from '../hooks/useBacktest'

interface BacktestConfigBarProps {
  params: BacktestParams
  onChange: (params: BacktestParams) => void
  disabled: boolean
  onRerun?: () => void
  canRerun?: boolean
}

export function BacktestConfigBar({ params, onChange, disabled, onRerun, canRerun }: BacktestConfigBarProps) {
  const update = (key: keyof BacktestParams, value: string | number) => {
    onChange({ ...params, [key]: value })
  }

  return (
    <div className="bg-white border-b border-slate-200 px-4 py-2 lg:px-6">
      <div className="flex flex-wrap items-center gap-3 max-w-screen-2xl mx-auto">
        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-slate-500">Symbol</label>
          <select
            value={params.symbol}
            onChange={(e) => update('symbol', e.target.value)}
            disabled={disabled}
            className="px-2 py-1 text-sm border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="BTCUSDT">BTC/USDT</option>
            <option value="ETHUSDT">ETH/USDT</option>
            <option value="BNBUSDT">BNB/USDT</option>
            <option value="SOLUSDT">SOL/USDT</option>
            <option value="XRPUSDT">XRP/USDT</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-slate-500">Timeframe</label>
          <select
            value={params.timeframe}
            onChange={(e) => update('timeframe', e.target.value)}
            disabled={disabled}
            className="px-2 py-1 text-sm border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="1h">1H</option>
            <option value="4h">4H</option>
            <option value="1d">1D</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-slate-500">Start</label>
          <input
            type="date"
            value={params.start_date}
            onChange={(e) => update('start_date', e.target.value)}
            disabled={disabled}
            className="px-2 py-1 text-sm border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-slate-500">End</label>
          <input
            type="date"
            value={params.end_date}
            onChange={(e) => update('end_date', e.target.value)}
            disabled={disabled}
            className="px-2 py-1 text-sm border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-slate-500">Capital</label>
          <input
            type="number"
            value={params.initial_capital}
            onChange={(e) => update('initial_capital', Number(e.target.value))}
            min={100}
            step={100}
            disabled={disabled}
            className="w-24 px-2 py-1 text-sm border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {canRerun && (
          <button
            onClick={onRerun}
            disabled={disabled}
            className="ml-auto flex items-center gap-1.5 px-3 py-1 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RotateCw className="w-3.5 h-3.5" />
            Rerun
          </button>
        )}
      </div>
    </div>
  )
}
