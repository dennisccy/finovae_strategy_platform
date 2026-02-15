import { useState } from 'react'
import { Loader2, Check, X, AlertCircle, CheckCircle2, Lightbulb, Code, ChevronDown, ChevronRight, User } from 'lucide-react'
import type { ActivityEntry } from '../hooks/useBacktest'

interface ActivityLogEntryProps {
  entry: ActivityEntry
  onEditAndRerun?: (iterationId: string) => void
  onSuggestionClick?: (prompt: string) => void
}

export function ActivityLogEntry({ entry, onEditAndRerun, onSuggestionClick }: ActivityLogEntryProps) {
  const [expanded, setExpanded] = useState(false)

  if (entry.type === 'user-prompt') {
    return (
      <div className="flex justify-end mb-3">
        <div className="flex items-start gap-2 max-w-[85%]">
          <div className="bg-primary-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed">
            {entry.content}
          </div>
          <div className="w-7 h-7 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0 mt-0.5">
            <User className="w-3.5 h-3.5 text-primary-600" />
          </div>
        </div>
      </div>
    )
  }

  if (entry.type === 'ai-step') {
    return (
      <div className="flex items-center gap-2.5 mb-2 ml-1">
        {entry.status === 'active' && (
          <Loader2 className="w-4 h-4 text-primary-500 animate-spin flex-shrink-0" />
        )}
        {entry.status === 'done' && (
          <div className="w-4 h-4 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
            <Check className="w-2.5 h-2.5 text-emerald-600" />
          </div>
        )}
        {entry.status === 'error' && (
          <div className="w-4 h-4 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
            <X className="w-2.5 h-2.5 text-red-600" />
          </div>
        )}
        {entry.status === 'pending' && (
          <div className="w-4 h-4 rounded-full border-2 border-slate-200 flex-shrink-0" />
        )}
        <span className={`text-sm ${
          entry.status === 'active' ? 'text-slate-800 font-medium' :
          entry.status === 'done' ? 'text-slate-500' :
          entry.status === 'error' ? 'text-red-600' :
          'text-slate-400'
        }`}>
          {entry.content}
        </span>
      </div>
    )
  }

  if (entry.type === 'code-preview') {
    return (
      <div className="mb-3 ml-1">
        <div className="bg-slate-50 border border-slate-200 rounded-xl overflow-hidden">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-slate-100 transition-colors"
          >
            <Code className="w-4 h-4 text-slate-500 flex-shrink-0" />
            <span className="text-sm font-medium text-slate-700 flex-1 truncate">{entry.content}</span>
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
            )}
          </button>
          {expanded && entry.detail && (
            <div className="border-t border-slate-200">
              <pre className="text-xs bg-slate-900 text-slate-100 p-3 overflow-x-auto max-h-64 overflow-y-auto">
                <code>{entry.detail}</code>
              </pre>
            </div>
          )}
          {entry.iterationId && onEditAndRerun && (
            <div className="border-t border-slate-200 px-3 py-2">
              <button
                onClick={() => onEditAndRerun(entry.iterationId!)}
                className="text-xs font-medium text-primary-600 hover:text-primary-700 transition-colors"
              >
                Edit & Re-run
              </button>
            </div>
          )}
        </div>
      </div>
    )
  }

  if (entry.type === 'error') {
    return (
      <div className="mb-3 ml-1">
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-red-700">{entry.content}</p>
        </div>
      </div>
    )
  }

  if (entry.type === 'complete') {
    return (
      <div className="mb-3 ml-1">
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 flex items-start gap-2.5">
          <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
          <p className="text-sm font-medium text-emerald-700">{entry.content}</p>
        </div>
      </div>
    )
  }

  if (entry.type === 'insights') {
    return (
      <div className="mb-3 ml-1">
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3">
          <div className="flex items-start gap-2.5">
            <Lightbulb className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-blue-800 leading-relaxed">{entry.content}</p>
              {entry.detail && onSuggestionClick && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {entry.detail.split(', ').map((suggestion, i) => (
                    <button
                      key={i}
                      onClick={() => onSuggestionClick(suggestion)}
                      className="px-2.5 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return null
}
