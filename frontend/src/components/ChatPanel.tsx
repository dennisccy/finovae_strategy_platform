import { useState, FormEvent } from 'react'
import { Loader2, Clock, Sparkles } from 'lucide-react'
import { RunHistoryItem } from '../hooks/useBacktest'

interface RecommendCard {
  id: string
  title: string
  description: string
  prompt: string
}

const recommendCards: RecommendCard[] = [
  {
    id: 'multi-factor',
    title: 'Multi-Factor Quantitative',
    description: 'Build a multi-factor trading strategy combining momentum, trend, and volatility signals. Each factor must confirm before entering a trade.',
    prompt: 'Build a quantitative multi-factor trading strategy that combines momentum, trend, and volatility technical dimensions to generate buy/sell signals. Each factor should confirm the others before entering, making the strategy more robust than any single indicator.',
  },
  {
    id: 'momentum-trend',
    title: 'Momentum Trend Following',
    description: 'Build a trend-following strategy that identifies and rides sustained price movements, entering on confirmed breakouts and exiting when the trend weakens.',
    prompt: 'Build a trend-following trading strategy that identifies and rides sustained price movements. Enter on confirmed trend breakouts and exit when the trend weakens or reverses.',
  },
  {
    id: 'volatility-breakout',
    title: 'Volatility Breakout',
    description: 'Build a volatility breakout strategy that detects low-volatility consolidation periods and enters when price breaks out of the range to capture the ensuing explosive move.',
    prompt: 'Build a volatility breakout trading strategy that detects low-volatility consolidation phases and enters when price breaks out of the consolidation range to capture the ensuing explosive move.',
  },
  {
    id: 'volume-momentum',
    title: 'Volume Momentum',
    description: 'Build a volume-confirmed momentum strategy that enters when price and volume expand together, and exits when volume contracts.',
    prompt: 'Build a volume momentum trading strategy that uses volume expansion to confirm price momentum direction. Enter when price and volume expand together, and exit when volume contracts or diverges.',
  },
]

interface ChatPanelProps {
  onGenerate: (naturalLanguage: string, model: string) => Promise<void>
  isLoading: boolean
  runHistory: RunHistoryItem[]
}

export function ChatPanel({ onGenerate, isLoading, runHistory }: ChatPanelProps) {
  const [strategy, setStrategy] = useState('')
  const [model, setModel] = useState('claude-haiku-4-5-20251001')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!strategy.trim() || isLoading) return
    await onGenerate(strategy, model)
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

      {/* AI Model Selection */}
      <div className="px-4 py-3 lg:px-6 lg:py-4 border-b border-slate-100 bg-slate-50">
        <label className="block text-xs font-medium text-slate-600 mb-1">
          AI Model
        </label>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full px-2.5 py-1.5 lg:px-3 lg:py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
        >
          <option value="claude-haiku-4-5-20251001">Claude Haiku 4.5 (Fast & Economical)</option>
          <option value="claude-sonnet-4-5-20250929">Claude Sonnet 4.5 (More Capable)</option>
        </select>
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
            placeholder="Example: Buy when RSI crosses below 30 and the price is above the 200-day moving average. Sell when RSI crosses above 70. Use a trailing stop of 2x ATR."
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
                Generating Strategy...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 lg:w-5 lg:h-5" />
                Generate Strategy
              </>
            )}
          </button>
        </div>

        {/* AI Recommendation Cards */}
        <div className="mt-3 lg:mt-4 pt-3 lg:pt-4 border-t border-slate-100">
          <p className="text-xs text-slate-500 mb-1.5 lg:mb-2">AI Recommended Strategies:</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 lg:gap-3">
            {recommendCards.map((card) => (
              <button
                key={card.id}
                type="button"
                disabled={isLoading}
                onClick={() => onGenerate(card.prompt, model)}
                className="text-left p-3 border border-slate-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <span className="block text-sm font-semibold text-slate-800">{card.title}</span>
                <span className="block mt-1 text-xs text-slate-500 leading-relaxed">{card.description}</span>
              </button>
            ))}
          </div>
        </div>
      </form>
    </div>
  )
}
