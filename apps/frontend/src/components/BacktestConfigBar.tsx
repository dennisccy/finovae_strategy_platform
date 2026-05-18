import { useState, useEffect } from 'react'
import { Square, Zap } from 'lucide-react'
import type { BacktestParams } from '../hooks/useBacktest'
import { EXCHANGE_CONFIGS } from '../hooks/useBacktest'

// API base convention shared across the app (mirrors useBacktest.ts:13 and the
// existing /api/config fetch). Empty string → relative /api/... via the Vite proxy.
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

interface TimeframeOption {
  value: string
  label: string
}

// Safe working defaults. Used while /api/symbols and /api/timeframes are in
// flight and as the fallback if either endpoint is unreachable, so the symbol
// and timeframe controls always stay usable and a backtest can still be run
// (J-01 / J-06 must not break when reference data is momentarily unavailable).
const FALLBACK_TIMEFRAMES: TimeframeOption[] = [
  { value: '1m', label: '1 Minute' },
  { value: '5m', label: '5 Minutes' },
  { value: '15m', label: '15 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: '1 Day' },
]

function isStringArray(v: unknown): v is string[] {
  return Array.isArray(v) && v.every((x) => typeof x === 'string')
}

function isTimeframeOption(v: unknown): v is TimeframeOption {
  if (typeof v !== 'object' || v === null) return false
  const o = v as Record<string, unknown>
  return typeof o.value === 'string' && typeof o.label === 'string'
}

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

  // Reference data fetched from the backend so the controls reflect what the
  // server actually supports instead of hardcoded frontend literals (J-05).
  // Self-contained fetch (no prop-drilling) — the smallest diff for this lean
  // change; BacktestConfigBar is the only UI surface that changes.
  const [symbolOptions, setSymbolOptions] = useState<string[]>([])
  const [timeframeOptions, setTimeframeOptions] = useState<TimeframeOption[]>(FALLBACK_TIMEFRAMES)

  useEffect(() => {
    let cancelled = false

    fetch(`${API_BASE_URL}/api/symbols`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data) => {
        if (cancelled) return
        const list = (data as { symbols?: unknown }).symbols
        if (isStringArray(list) && list.length > 0) setSymbolOptions(list)
      })
      .catch(() => {
        /* Endpoint unreachable: the symbol field stays a usable free-text
           input (no suggestions) and existing defaults still run a backtest. */
      })

    fetch(`${API_BASE_URL}/api/timeframes`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data) => {
        if (cancelled) return
        const raw = (data as { timeframes?: unknown }).timeframes
        if (Array.isArray(raw)) {
          const valid = (raw as unknown[]).filter(isTimeframeOption)
          if (valid.length > 0) setTimeframeOptions(valid)
        }
      })
      .catch(() => {
        /* Endpoint unreachable: keep FALLBACK_TIMEFRAMES so the timeframe
           control stays usable and the current selection is unaffected. */
      })

    return () => {
      cancelled = true
    }
  }, [])

  // Guarantee the active selection is always selectable so wiring the options
  // never silently changes the effective default that flows into a backtest.
  const timeframeChoices = timeframeOptions.some((t) => t.value === params.timeframe)
    ? timeframeOptions
    : [{ value: params.timeframe, label: params.timeframe }, ...timeframeOptions]

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
              list="symbol-options"
              value={params.symbol}
              onChange={(e) => handleSymbolChange(e.target.value)}
              onBlur={(e) => handleSymbolChange(e.target.value.trim())}
              disabled={disabled}
              placeholder="e.g. PEPE/USDT"
              className={`w-28 px-2 py-1 text-sm border rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white disabled:opacity-50 disabled:cursor-not-allowed ${
                symbolError ? 'border-red-400' : 'border-slate-200'
              }`}
            />
            <datalist id="symbol-options">
              {symbolOptions.map((s) => (
                <option key={s} value={s} />
              ))}
            </datalist>
            {symbolError && <span className="text-xs text-red-500">{symbolError}</span>}
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-slate-500">Timeframe</label>
          <select
            value={params.timeframe}
            onChange={(e) => update('timeframe', e.target.value)}
            disabled={disabled}
            className="px-2 py-1 text-sm border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {timeframeChoices.map((tf) => (
              <option key={tf.value} value={tf.value}>{tf.label}</option>
            ))}
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

        <div className="flex items-center gap-1.5">
          <label className="flex items-center gap-1 text-xs font-medium text-slate-500 cursor-pointer select-none">
            <input type="checkbox"
              checked={params.max_order_size_pct !== undefined}
              onChange={(e) => onChange({ ...params,
                max_order_size_pct: e.target.checked ? 0.10 : undefined })}
              disabled={disabled}
              className="rounded border-slate-300 text-primary-600 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            Max Order
          </label>
          {params.max_order_size_pct !== undefined && (
            <div className="flex items-center gap-0.5">
              <input type="number"
                value={Math.round(params.max_order_size_pct * 100)}
                onChange={(e) => onChange({ ...params,
                  max_order_size_pct: Math.min(100, Math.max(1, Number(e.target.value))) / 100 })}
                min={1} max={100} step={1} disabled={disabled}
                className="w-12 px-1 py-1 text-sm border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white disabled:opacity-50 disabled:cursor-not-allowed text-center"
              />
              <span className="text-xs text-slate-400">%</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <label className="flex items-center gap-1 text-xs font-medium text-slate-500 cursor-pointer select-none">
            <input type="checkbox"
              checked={params.max_daily_loss_pct !== undefined}
              onChange={(e) => onChange({ ...params,
                max_daily_loss_pct: e.target.checked ? 0.05 : undefined })}
              disabled={disabled}
              className="rounded border-slate-300 text-primary-600 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            Max Loss/Day
          </label>
          {params.max_daily_loss_pct !== undefined && (
            <div className="flex items-center gap-0.5">
              <input type="number"
                value={Math.round(params.max_daily_loss_pct * 100)}
                onChange={(e) => onChange({ ...params,
                  max_daily_loss_pct: Math.min(100, Math.max(1, Number(e.target.value))) / 100 })}
                min={1} max={100} step={1} disabled={disabled}
                className="w-12 px-1 py-1 text-sm border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white disabled:opacity-50 disabled:cursor-not-allowed text-center"
              />
              <span className="text-xs text-slate-400">%</span>
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
