import { RotateCw, Square, Zap } from 'lucide-react'
import type { BacktestParams } from '../hooks/useBacktest'
import { EXCHANGE_CONFIGS } from '../hooks/useBacktest'

interface BacktestConfigBarProps {
  params: BacktestParams
  onChange: (params: BacktestParams) => void
  disabled: boolean
  onRerun?: () => void
  canRerun?: boolean
  isAutoRunning?: boolean
  autoRunProgress?: { current: number; max: number } | null
  canAutoRun?: boolean
  onStartAutoRun?: () => void
  onStopAutoRun?: () => void
  autoRunCount?: number
  onAutoRunCountChange?: (n: number) => void
}

export function BacktestConfigBar({ params, onChange, disabled, onRerun, canRerun, isAutoRunning, autoRunProgress, canAutoRun, onStartAutoRun, onStopAutoRun, autoRunCount, onAutoRunCountChange }: BacktestConfigBarProps) {
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

        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-slate-500">Exchange</label>
          <select
            value={params.exchange}
            onChange={(e) => update('exchange', e.target.value)}
            disabled={disabled}
            className="px-2 py-1 text-sm border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {Object.entries(EXCHANGE_CONFIGS).map(([key, cfg]) => (
              <option key={key} value={key}>{cfg.label} ({parseFloat((cfg.commission * 100).toFixed(3))}%)</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <label className="flex items-center gap-1 text-xs font-medium text-slate-500 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={params.allow_short ?? false}
              onChange={(e) => onChange({ ...params, allow_short: e.target.checked })}
              disabled={disabled}
              className="rounded border-slate-300 text-primary-600 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            Shorts
          </label>
        </div>

        <div className="flex items-center gap-1.5">
          <label className="flex items-center gap-1 text-xs font-medium text-slate-500 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={(params.leverage ?? 1) > 1}
              onChange={(e) => onChange({ ...params, leverage: e.target.checked ? (params.leverage && params.leverage > 1 ? params.leverage : 2) : 1 })}
              disabled={disabled}
              className="rounded border-slate-300 text-primary-600 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            Leverage
          </label>
          {(params.leverage ?? 1) > 1 && (
            <div className="flex items-center gap-0.5">
              <input
                type="number"
                value={params.leverage ?? 2}
                onChange={(e) => onChange({ ...params, leverage: Math.min(10, Math.max(1, Number(e.target.value))) })}
                min={1}
                max={10}
                step={1}
                disabled={disabled}
                className="w-10 px-1 py-1 text-sm border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white disabled:opacity-50 disabled:cursor-not-allowed text-center"
              />
              <span className="text-xs text-slate-400">x</span>
            </div>
          )}
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
        {isAutoRunning ? (
          <button
            onClick={onStopAutoRun}
            className="flex items-center gap-1.5 px-3 py-1 text-sm font-medium text-white bg-amber-500 hover:bg-amber-600 rounded-md transition-colors"
          >
            <Square className="w-3.5 h-3.5" />
            Stop ({autoRunProgress?.current ?? 0}/{autoRunProgress?.max ?? 10})
          </button>
        ) : (
          canAutoRun && (
            <div className="flex items-center gap-1">
              <button
                onClick={onStartAutoRun}
                disabled={disabled}
                className="flex items-center gap-1.5 px-3 py-1 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Zap className="w-3.5 h-3.5" />
                Auto Run ({autoRunCount ?? 10})
              </button>
              <input
                type="number"
                min={1}
                max={100}
                step={1}
                value={autoRunCount ?? 10}
                onChange={e => onAutoRunCountChange?.(Math.max(1, Math.min(100, Number(e.target.value))))}
                onClick={e => e.stopPropagation()}
                className="w-12 px-1 py-0.5 text-xs border border-slate-300 rounded text-center"
              />
            </div>
          )
        )}
      </div>
    </div>
  )
}
