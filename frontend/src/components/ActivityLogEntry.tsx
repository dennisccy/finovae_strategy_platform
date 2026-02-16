import { useState, useEffect } from 'react'
import { Loader2, Check, X, AlertCircle, CheckCircle2, Lightbulb, Code, ChevronDown, ChevronRight, User } from 'lucide-react'
import type { ActivityEntry } from '../hooks/useBacktest'

function ElapsedTimer({ startedAt }: { startedAt: number }) {
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 100)
    return () => clearInterval(id)
  }, [])

  const elapsed = ((now - startedAt) / 1000).toFixed(1)
  return <span className="text-xs text-slate-400 tabular-nums ml-1">{elapsed}s</span>
}

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
    const isSub = entry.substep
    const iconSize = isSub ? 'w-3 h-3' : 'w-4 h-4'
    const innerIcon = isSub ? 'w-2 h-2' : 'w-2.5 h-2.5'
    const textSize = isSub ? 'text-xs' : 'text-sm'

    return (
      <div className={`flex items-center gap-2.5 mb-1.5 ${isSub ? 'ml-7' : 'ml-1'}`}>
        {entry.status === 'active' && (
          <Loader2 className={`${iconSize} text-primary-500 animate-spin flex-shrink-0`} />
        )}
        {entry.status === 'done' && (
          <div className={`${iconSize} rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0`}>
            <Check className={`${innerIcon} text-emerald-600`} />
          </div>
        )}
        {entry.status === 'error' && (
          <div className={`${iconSize} rounded-full bg-red-100 flex items-center justify-center flex-shrink-0`}>
            <X className={`${innerIcon} text-red-600`} />
          </div>
        )}
        {entry.status === 'pending' && (
          <div className={`${iconSize} rounded-full border-2 border-slate-200 flex-shrink-0`} />
        )}
        <span className={`${textSize} ${
          entry.status === 'active' ? (isSub ? 'text-slate-700 font-medium' : 'text-slate-800 font-medium') :
          entry.status === 'done' ? (isSub ? 'text-slate-400' : 'text-slate-500') :
          entry.status === 'error' ? 'text-red-600' :
          'text-slate-400'
        }`}>
          {entry.content}
        </span>
        {entry.status === 'active' && entry.startedAt != null && (
          <ElapsedTimer startedAt={entry.startedAt} />
        )}
        {(entry.status === 'done' || entry.status === 'error') && entry.startedAt != null && entry.completedAt != null && (
          <span className="text-xs text-slate-400 tabular-nums ml-1">
            {((entry.completedAt - entry.startedAt) / 1000).toFixed(1)}s
          </span>
        )}
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
    // Parse suggestions from JSON detail (array of {title, description, prompt})
    let suggestions: Array<{ title: string; description: string; prompt: string }> = []
    if (entry.detail) {
      try {
        suggestions = JSON.parse(entry.detail)
      } catch {
        // Fallback for legacy comma-separated format
        suggestions = entry.detail.split(', ').map(t => ({ title: t, description: '', prompt: t }))
      }
    }

    return (
      <div className="mb-3 ml-1">
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3">
          <div className="flex items-start gap-2.5">
            <Lightbulb className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-blue-800 leading-relaxed">{entry.content}</p>
              {suggestions.length > 0 && onSuggestionClick && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => onSuggestionClick(s.prompt)}
                      title={s.description}
                      className="px-2.5 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
                    >
                      {s.title}
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
