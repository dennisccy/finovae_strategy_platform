import { useState, FormEvent } from 'react'
import Editor from 'react-simple-code-editor'
import { highlight, languages } from 'prismjs'
import 'prismjs/components/prism-python'
import 'prismjs/themes/prism.css'
import { Play, RefreshCw, Loader2, AlertTriangle } from 'lucide-react'
import { GeneratedScript } from '../hooks/useBacktest'

interface ScriptReviewPanelProps {
  script: GeneratedScript
  scriptCode: string
  onScriptCodeChange: (code: string) => void
  onExecute: (params: {
    script_id: string
    script_code?: string
    symbol: string
    timeframe: string
    start_date: string
    end_date: string
    initial_capital: number
  }) => Promise<void>
  onRegenerate: () => void
  isLoading: boolean
  error: string | null
}

export function ScriptReviewPanel({
  script,
  scriptCode,
  onScriptCodeChange,
  onExecute,
  onRegenerate,
  isLoading,
  error,
}: ScriptReviewPanelProps) {
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [timeframe, setTimeframe] = useState('4h')
  const [startDate, setStartDate] = useState('2024-01-01')
  const [endDate, setEndDate] = useState('2024-06-01')
  const [capital, setCapital] = useState(10000)

  const isEdited = scriptCode !== script.script_code

  const handleExecute = async (e: FormEvent) => {
    e.preventDefault()
    if (isLoading) return

    await onExecute({
      script_id: script.script_id,
      script_code: isEdited ? scriptCode : undefined,
      symbol,
      timeframe,
      start_date: startDate,
      end_date: endDate,
      initial_capital: capital,
    })
  }

  return (
    <div className="flex flex-col h-full bg-white overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 lg:px-6 lg:py-4 border-b border-slate-200 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <h2 className="text-base lg:text-lg font-semibold text-slate-800">
              {script.strategy_name || 'Generated Strategy'}
            </h2>
            <p className="text-xs lg:text-sm text-slate-500 mt-0.5 truncate">
              {script.strategy_description || 'Review the generated script before running'}
            </p>
          </div>
          <button
            onClick={onRegenerate}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 disabled:opacity-50 transition-colors flex-shrink-0 ml-3"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Regenerate
          </button>
        </div>
        {isEdited && (
          <div className="mt-2 flex items-center gap-1.5 text-xs text-amber-600">
            <AlertTriangle className="w-3.5 h-3.5" />
            Script modified - will be re-validated on execution
          </div>
        )}
        {script.validation_errors.length > 0 && (
          <div className="mt-2 p-2 bg-red-50 rounded-lg">
            <p className="text-xs font-medium text-red-700">Validation warnings:</p>
            {script.validation_errors.map((err, i) => (
              <p key={i} className="text-xs text-red-600 mt-0.5">{err}</p>
            ))}
          </div>
        )}
      </div>

      {/* Code Editor */}
      <div className="flex-1 overflow-y-auto border-b border-slate-200">
        <div className="min-h-full">
          <Editor
            value={scriptCode}
            onValueChange={onScriptCodeChange}
            highlight={code => highlight(code, languages.python, 'python')}
            padding={16}
            style={{
              fontFamily: '"Fira Code", "Fira Mono", monospace',
              fontSize: 13,
              lineHeight: 1.5,
              minHeight: '100%',
            }}
            className="code-editor"
          />
        </div>
      </div>

      {/* Backtest Config & Execute */}
      <form onSubmit={handleExecute} className="px-4 py-3 lg:px-6 lg:py-4 bg-slate-50 flex-shrink-0">
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Symbol</label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-full px-2.5 py-1.5 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
            >
              <option value="BTCUSDT">BTC/USDT</option>
              <option value="ETHUSDT">ETH/USDT</option>
              <option value="BNBUSDT">BNB/USDT</option>
              <option value="SOLUSDT">SOL/USDT</option>
              <option value="XRPUSDT">XRP/USDT</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Timeframe</label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="w-full px-2.5 py-1.5 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
            >
              <option value="1h">1 Hour</option>
              <option value="4h">4 Hours</option>
              <option value="1d">1 Day</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-2.5 py-1.5 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-2.5 py-1.5 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
            />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-slate-600 mb-1">Initial Capital (USDT)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              min={100}
              step={100}
              className="w-full px-2.5 py-1.5 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
            />
          </div>
        </div>

        {error && (
          <div className="mb-3 p-2 bg-red-50 rounded-lg">
            <p className="text-xs text-red-600">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Running Backtest...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Run Backtest
            </>
          )}
        </button>
      </form>
    </div>
  )
}
