import { useState, FormEvent } from 'react'
import { Lightbulb, ChevronRight, Send, Loader2, Clock } from 'lucide-react'
import type { StrategyInsights, RunHistoryItem } from '../hooks/useBacktest'

interface InsightsPanelProps {
  insights: StrategyInsights | null
  insightsLoading: boolean
  onIterate: (prompt: string, model: string, previousScriptCode: string) => Promise<void>
  onGenerateInsights: (model: string) => Promise<void>
  isLoading: boolean
  scriptCode: string | null
  runHistory: RunHistoryItem[]
}

export function InsightsPanel({
  insights,
  insightsLoading,
  onIterate,
  onGenerateInsights,
  isLoading,
  scriptCode,
  runHistory,
}: InsightsPanelProps) {
  const [customPrompt, setCustomPrompt] = useState('')
  const [model, setModel] = useState('claude-haiku-4-5-20251001')

  const handleSuggestionClick = async (prompt: string) => {
    if (isLoading || !scriptCode) return
    await onIterate(prompt, model, scriptCode)
  }

  const handleCustomSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!customPrompt.trim() || isLoading || !scriptCode) return
    const prompt = customPrompt
    setCustomPrompt('')
    await onIterate(prompt, model, scriptCode)
  }

  const handleRegenerateInsights = async () => {
    if (insightsLoading) return
    await onGenerateInsights(model)
  }

  const formatReturn = (value: number) => {
    const percent = (value * 100).toFixed(2)
    return value >= 0 ? `+${percent}%` : `${percent}%`
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="px-4 py-3 lg:px-6 lg:py-4 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-amber-500" />
          <h2 className="text-base lg:text-lg font-semibold text-slate-800">Strategy Insights</h2>
        </div>
        <p className="text-xs lg:text-sm text-slate-500 mt-0.5 lg:mt-1">
          AI-powered analysis and improvement suggestions
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

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-4">
        {/* Loading State */}
        {insightsLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <Loader2 className="w-8 h-8 animate-spin text-primary-500 mx-auto mb-3" />
              <p className="text-sm text-slate-500">Analyzing strategy performance...</p>
            </div>
          </div>
        )}

        {/* Summary Card */}
        {insights?.summary && !insightsLoading && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <Lightbulb className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="text-sm font-semibold text-blue-900 mb-1.5">Analysis Summary</h3>
                <p className="text-sm text-blue-800 leading-relaxed">{insights.summary}</p>
              </div>
            </div>
          </div>
        )}

        {/* Suggestion Cards */}
        {insights?.suggestions && insights.suggestions.length > 0 && !insightsLoading && (
          <div>
            <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
              Improvement Suggestions
            </h3>
            <div className="space-y-2">
              {insights.suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion.prompt)}
                  disabled={isLoading}
                  className="w-full text-left p-3 lg:p-4 border border-slate-200 rounded-xl hover:border-primary-300 hover:bg-primary-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors group"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-semibold text-slate-800 group-hover:text-primary-700">
                        {suggestion.title}
                      </h4>
                      <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                        {suggestion.description}
                      </p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-primary-500 mt-0.5 flex-shrink-0" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* No insights yet and not loading */}
        {!insights && !insightsLoading && (
          <div className="flex flex-col items-center justify-center py-12">
            <Lightbulb className="w-10 h-10 text-slate-300 mb-3" />
            <p className="text-sm text-slate-500 mb-3">No insights generated yet</p>
            <button
              onClick={handleRegenerateInsights}
              className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              Generate Insights
            </button>
          </div>
        )}
      </div>

      {/* Custom Input — pinned to bottom */}
      <div className="border-t border-slate-200 p-4 lg:p-6">
        <form onSubmit={handleCustomSubmit} className="flex gap-2">
          <input
            type="text"
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            placeholder="Describe how to improve the strategy..."
            disabled={isLoading || !scriptCode}
            className="flex-1 px-3 py-2 lg:px-4 lg:py-2.5 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-slate-50 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!customPrompt.trim() || isLoading || !scriptCode}
            className="px-3 py-2 lg:px-4 lg:py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
