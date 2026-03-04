import { useState } from 'react'
import { AlertTriangle, Check, Globe, Play } from 'lucide-react'
import type { VideoResult } from '../hooks/useVideoStrategy'

interface ExtractedStrategyCardProps {
  result: VideoResult
  onRunBacktest: (prompt: string) => void
  disabled?: boolean
}

function confidenceColor(confidence: number): string {
  if (confidence >= 0.7) return 'text-green-600 bg-green-50 border-green-200'
  if (confidence >= 0.4) return 'text-amber-600 bg-amber-50 border-amber-200'
  return 'text-red-600 bg-red-50 border-red-200'
}

function confidenceLabel(confidence: number): string {
  if (confidence >= 0.7) return 'High'
  if (confidence >= 0.4) return 'Medium'
  return 'Low'
}

export function ExtractedStrategyCard({ result, onRunBacktest, disabled = false }: ExtractedStrategyCardProps) {
  const [editedPrompt, setEditedPrompt] = useState(result.natural_language_prompt)

  const handleRun = () => {
    onRunBacktest(editedPrompt)
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-800 truncate">{result.strategy_name}</h3>
          <p className="text-sm text-slate-500 mt-0.5">{result.strategy_description}</p>
        </div>
        <div className={`flex-shrink-0 px-2 py-0.5 text-xs font-medium border rounded-full ${confidenceColor(result.confidence)}`}>
          {confidenceLabel(result.confidence)} ({Math.round(result.confidence * 100)}%)
        </div>
      </div>

      {/* Source Info */}
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <span className="font-medium text-slate-600">{result.title}</span>
        <span>by {result.channel}</span>
        {result.was_translated && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded">
            <Globe className="h-3 w-3" />
            Translated from {result.transcript_language}
          </span>
        )}
        {result.cached && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded">
            <Check className="h-3 w-3" />
            Cached
          </span>
        )}
      </div>

      {/* Warnings */}
      {result.warnings.length > 0 && (
        <div className="space-y-1">
          {result.warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-2 p-2 bg-amber-50 rounded text-xs text-amber-700">
              <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Editable Prompt */}
      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">
          Strategy Prompt (editable)
        </label>
        <textarea
          value={editedPrompt}
          onChange={(e) => setEditedPrompt(e.target.value)}
          rows={4}
          className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-y"
          disabled={disabled}
        />
      </div>

      {/* Run Backtest Button */}
      <button
        onClick={handleRun}
        disabled={disabled || !editedPrompt.trim()}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <Play className="h-4 w-4" />
        Run Backtest with Extracted Strategy
      </button>
    </div>
  )
}
