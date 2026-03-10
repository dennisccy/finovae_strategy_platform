import { useState } from 'react'
import { Square, Zap } from 'lucide-react'
import type { BacktestParams } from '../hooks/useBacktest'
import { EXCHANGE_CONFIGS } from '../hooks/useBacktest'

interface BacktestConfigBarProps {
  params: BacktestParams
  onChange: (params: BacktestParams) => void
  disabled: boolean
  isAutoRunning?: boolean
  autoRunProgress?: { current: number; max: number } | null
  canAutoRun?: boolean
  onStartAutoRun?: () => void
  onStopAutoRun?: () => void
  autoRunCount?: number
  onAutoRunCountChange?: (n: number) => void
  workerCount?: number
}

export function BacktestConfigBar({ params, onChange, disabled, isAutoRunning, autoRunProgress, canAutoRun, onStartAutoRun, onStopAutoRun, autoRunCount, onAutoRunCountChange, workerCount }: BacktestConfigBarProps) {
  const [symbolError, setSymbolError] = useState<string | null>(null)

  const update = (key: keyof BacktestParams, value: string | number) => {
    onChange({ ...params, [key]: value })
  }

  const handleSymbolChange = (val: string) => {
    const upper = val.toUpperCase()
    update('symbol', upper)
    if (upper && !/^[A-Z]+\/USDT$/.test(upper)) {
      setSymbolError('Must be BASE/USDT format (e.g. PEPE/USDT)')
    } else {
      setSymbolError(null)
    }
  }

  return (
    <div className="bg-white border-b border-slate-200 px-4 py-2 lg:px-6">
      <div className="flex flex-wrap items-center gap-3 max-w-screen-2xl mx-auto">
        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-slate-500">Symbol</label>
          <div className="flex flex-col gap-0.5">
            <input
              type="text"
              value={params.symbol}
              onChange={(e) => handleSymbolChange(e.target.value)}
              onBlur={(e) => handleSymbolChange(e.target.value.trim())}
              disabled={disabled}
              placeholder="e.g. PEPE/USDT"
              className={`w-28 px-2 py-1 text-sm border rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white disabled:opacity-50 disabled:cursor-not-allowed ${
                symbolError ? 'border-red-400' : 'border-slate-200'
              }`}
            />
            {symbolError && <span className="text-xs text-red-500">{symbolError}</span>}
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-slate-500">Timeframe</label>
          <div className="flex gap-0.5">
            {(['1m', '5m', '15m', '1h', '4h', '1d'] as const).map(tf => {
              const selected = params.timeframe === tf
              return (
                <button
                  key={tf}
                  type="button"
                  disabled={disabled}
                  onClick={() => { if (!selected) onChange({ ...params, timeframe: tf }) }}
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

        {isAutoRunning ? (
          <button
            onClick={onStopAutoRun}
            className="ml-auto flex items-center gap-1.5 px-3 py-1 text-sm font-medium text-white bg-amber-500 hover:bg-amber-600 rounded-md transition-colors"
          >
            <Square className="w-3.5 h-3.5" />
            Stop ({autoRunProgress?.current ?? 0}/{autoRunProgress?.max ?? 10})
          </button>
        ) : (
          canAutoRun && (
            <div className="ml-auto flex items-center gap-1">
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
              {workerCount !== undefined && (
                <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${
                  workerCount > 1 ? 'bg-violet-100 text-violet-600' : 'bg-slate-100 text-slate-500'
                }`}>
                  {workerCount}w
                </span>
              )}
            </div>
          )
        )}
      </div>
    </div>
  )
}
