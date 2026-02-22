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
            <option value="ADAUSDT">ADA/USDT</option>
            <option value="DOGEUSDT">DOGE/USDT</option>
            <option value="AVAXUSDT">AVAX/USDT</option>
            <option value="DOTUSDT">DOT/USDT</option>
            <option value="LINKUSDT">LINK/USDT</option>
            <option value="MATICUSDT">MATIC/USDT</option>
            <option value="UNIUSDT">UNI/USDT</option>
            <option value="LTCUSDT">LTC/USDT</option>
            <option value="ATOMUSDT">ATOM/USDT</option>
            <option value="NEARUSDT">NEAR/USDT</option>
            <option value="ARBUSDT">ARB/USDT</option>
            <option value="OPUSDT">OP/USDT</option>
            <option value="SUIUSDT">SUI/USDT</option>
            <option value="APTUSDT">APT/USDT</option>
            <option value="INJUSDT">INJ/USDT</option>
            <option value="TIAUSDT">TIA/USDT</option>
            <option value="SEIUSDT">SEI/USDT</option>
            <option value="FETUSDT">FET/USDT</option>
            <option value="RENDERUSDT">RENDER/USDT</option>
            <option value="WLDUSDT">WLD/USDT</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-slate-500">Timeframes</label>
          <div className="flex gap-0.5">
            {(['1m', '5m', '15m', '1h', '4h', '1d'] as const).map(tf => {
              const current: string[] = Array.isArray(params.timeframes) ? params.timeframes : ['4h']
              const selected = current[0] === tf
              return (
                <button
                  key={tf}
                  type="button"
                  disabled={disabled}
                  onClick={() => {
                    if (!selected) {
                      onChange({ ...params, timeframes: [tf] })
                    }
                  }}
                  className={`px-2 py-1 text-xs font-medium rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                    selected
                      ? 'bg-primary-600 text-white'
                      : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                  }`}
                >
                  {tf === '1d' ? '1D' : tf}
                </button>
              )
            })}
          </div>
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
