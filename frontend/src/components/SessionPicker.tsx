import { useState, useRef, useEffect } from 'react'
import { FilePlus, ChevronDown, Trash2, Clock, BarChart3 } from 'lucide-react'
import type { ArchivedSession } from '../hooks/useBacktest'

interface SessionPickerProps {
  archivedSessions: ArchivedSession[]
  hasCurrentIterations: boolean
  isLoading: boolean
  onNewSession: () => void
  onSwitchSession: (id: string) => void
  onDeleteSession: (id: string) => void
}

export function SessionPicker({
  archivedSessions,
  hasCurrentIterations,
  isLoading,
  onNewSession,
  onSwitchSession,
  onDeleteSession,
}: SessionPickerProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Hidden when nothing to show
  if (!hasCurrentIterations && archivedSessions.length === 0) return null

  // Simple button when no archive exists
  if (archivedSessions.length === 0) {
    return (
      <button
        onClick={onNewSession}
        disabled={isLoading}
        className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        title="Start a new session"
      >
        <FilePlus className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">New Session</span>
      </button>
    )
  }

  // Dropdown when archive has entries
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={isLoading}
        className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Clock className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">Sessions</span>
        <span className="w-4 h-4 rounded-full bg-primary-100 text-primary-600 text-[10px] flex items-center justify-center font-semibold">
          {archivedSessions.length}
        </span>
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-72 bg-white border border-slate-200 rounded-lg shadow-lg z-50">
          {/* New Session action */}
          {hasCurrentIterations && (
            <button
              onClick={() => { onNewSession(); setOpen(false) }}
              className="w-full flex items-center gap-2 px-3 py-2.5 text-xs font-medium text-primary-600 hover:bg-primary-50 border-b border-slate-100 transition-colors"
            >
              <FilePlus className="w-3.5 h-3.5" />
              New Session
            </button>
          )}

          {/* Archived sessions list */}
          <div className="max-h-64 overflow-y-auto">
            {archivedSessions.map(session => (
              <div
                key={session.id}
                className="flex items-center gap-2 px-3 py-2.5 hover:bg-slate-50 border-b border-slate-50 last:border-0 cursor-pointer group transition-colors"
                onClick={() => { onSwitchSession(session.id); setOpen(false) }}
              >
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-slate-700 truncate">
                    {session.name}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-slate-400">
                      {new Date(session.createdAt).toLocaleDateString()}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {session.iterationCount} iter{session.iterationCount !== 1 ? 's' : ''}
                    </span>
                    {session.bestReturn !== null && (
                      <span className={`text-[10px] font-medium flex items-center gap-0.5 ${
                        session.bestReturn >= 0 ? 'text-emerald-500' : 'text-red-500'
                      }`}>
                        <BarChart3 className="w-2.5 h-2.5" />
                        {session.bestReturn >= 0 ? '+' : ''}{(session.bestReturn * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteSession(session.id)
                  }}
                  className="p-1 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded opacity-0 group-hover:opacity-100 transition-all"
                  title="Delete session"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
