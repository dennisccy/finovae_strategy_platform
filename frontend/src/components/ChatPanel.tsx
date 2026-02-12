import { useState, FormEvent } from 'react'
import { Loader2, Clock, TrendingUp } from 'lucide-react'
import { BacktestRequest, RunHistoryItem } from '../hooks/useBacktest'

interface ChatPanelProps {
  onSubmit: (request: BacktestRequest) => Promise<void>
  isLoading: boolean
  runHistory: RunHistoryItem[]
}

export function ChatPanel({ onSubmit, isLoading, runHistory }: ChatPanelProps) {
  const [strategy, setStrategy] = useState('')
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [timeframe, setTimeframe] = useState('4h')
  const [startDate, setStartDate] = useState('2024-01-01')
  const [endDate, setEndDate] = useState('2024-06-01')
  const [capital, setCapital] = useState(10000)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!strategy.trim() || isLoading) return

    await onSubmit({
      natural_language: strategy,
      symbol,
      timeframe,
      start_date: startDate,
      end_date: endDate,
      initial_capital: capital,
    })
  }

  const formatReturn = (value: number) => {
    const percent = (value * 100).toFixed(2)
    return value >= 0 ? `+${percent}%` : `${percent}%`
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Panel Header */}
      <div className="px-4 py-3 lg:px-6 lg:py-4 border-b border-slate-200">
        <h2 className="text-base lg:text-lg font-semibold text-slate-800">Strategy Builder</h2>
        <p className="text-xs lg:text-sm text-slate-500 mt-0.5 lg:mt-1">
          Describe your trading strategy in plain English
        </p>
      </div>

      {/* Configuration Section */}
      <div className="px-4 py-3 lg:px-6 lg:py-4 border-b border-slate-100 bg-slate-50">
        <div className="grid grid-cols-2 gap-3 lg:gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Symbol
            </label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-full px-2.5 py-1.5 lg:px-3 lg:py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
            >
              <option value="BTCUSDT">BTC/USDT</option>
              <option value="ETHUSDT">ETH/USDT</option>
              <option value="BNBUSDT">BNB/USDT</option>
              <option value="SOLUSDT">SOL/USDT</option>
              <option value="XRPUSDT">XRP/USDT</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Timeframe
            </label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="w-full px-2.5 py-1.5 lg:px-3 lg:py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
            >
              <option value="1h">1 Hour</option>
              <option value="4h">4 Hours</option>
              <option value="1d">1 Day</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-2.5 py-1.5 lg:px-3 lg:py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-2.5 py-1.5 lg:px-3 lg:py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
            />
          </div>

          <div className="col-span-2">
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Initial Capital (USDT)
            </label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              min={100}
              step={100}
              className="w-full px-2.5 py-1.5 lg:px-3 lg:py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
            />
          </div>
        </div>
      </div>

      {/* Run History */}
      {runHistory.length > 0 && (
        <div className="px-4 py-2.5 lg:px-6 lg:py-3 border-b border-slate-100 max-h-28 lg:max-h-40 overflow-y-auto">
          <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1.5 lg:mb-2">
            Recent Runs
          </h3>
          <div className="space-y-1.5">
            {runHistory.slice(0, 5).map((run) => (
              <div
                key={run.run_id}
                className="flex items-center justify-between p-1.5 lg:p-2 bg-slate-50 rounded-lg text-xs lg:text-sm"
              >
                <div className="flex items-center gap-1.5 lg:gap-2 flex-1 min-w-0">
                  <Clock className="w-3.5 h-3.5 lg:w-4 lg:h-4 text-slate-400 flex-shrink-0" />
                  <span className="truncate text-slate-600">
                    {run.natural_language.slice(0, 30)}...
                  </span>
                </div>
                <div className="flex items-center flex-shrink-0 ml-2">
                  <span
                    className={`font-medium ${
                      run.total_return >= 0 ? 'text-emerald-600' : 'text-red-600'
                    }`}
                  >
                    {formatReturn(run.total_return)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strategy Input */}
      <form onSubmit={handleSubmit} className="flex-1 flex flex-col p-4 lg:p-6">
        <div className="flex-1">
          <label className="block text-sm font-medium text-slate-700 mb-1.5 lg:mb-2">
            Strategy Description
          </label>
          <textarea
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            placeholder="Example: Buy when RSI crosses below 30 and the price is above the 200-day moving average. Sell when RSI crosses above 70."
            className="w-full h-24 sm:h-32 lg:h-48 px-3 py-2.5 lg:px-4 lg:py-3 text-sm border border-slate-200 rounded-lg resize-none focus:ring-2 focus:ring-primary-500 focus:border-transparent chat-input"
            disabled={isLoading}
          />
        </div>

        <div className="mt-3 lg:mt-4">
          <button
            type="submit"
            disabled={!strategy.trim() || isLoading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 lg:px-6 lg:py-3 bg-primary-600 text-white text-sm lg:text-base font-medium rounded-lg hover:bg-primary-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 lg:w-5 lg:h-5 animate-spin" />
                Running Backtest...
              </>
            ) : (
              <>
                <TrendingUp className="w-4 h-4 lg:w-5 lg:h-5" />
                Run Backtest
              </>
            )}
          </button>
        </div>

        {/* Example Strategies */}
        <div className="mt-3 lg:mt-4 pt-3 lg:pt-4 border-t border-slate-100">
          <p className="text-xs text-slate-500 mb-1.5 lg:mb-2">Try an example:</p>
          <div className="flex flex-wrap gap-1.5 lg:gap-2">
            {[
              'Buy when RSI < 30, sell when RSI > 70',
              'Buy when price crosses above SMA(50)',
              'Buy when MACD crosses above signal line',
            ].map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => setStrategy(example)}
                className="px-2.5 py-1 text-xs bg-slate-100 text-slate-600 rounded-full hover:bg-slate-200 transition-colors leading-tight"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </form>
    </div>
  )
}
