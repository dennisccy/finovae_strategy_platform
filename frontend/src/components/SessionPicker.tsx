import { useState, useRef, useEffect } from 'react'
import { FilePlus, ChevronDown, Trash2, BarChart3, Clock } from 'lucide-react'
import type { ArchivedSession, LiveSessionStatus } from '../hooks/useBacktest'

interface SessionPickerProps {
  liveSessions: LiveSessionStatus[]
  activeSessionId: string
  archivedSessions: ArchivedSession[]
  onSelectLive: (id: string) => void
  onNewSession: () => void
  onRestoreArchived: (id: string) => void
  onDeleteArchived: (id: string) => void
  onDeleteLive: (id: string) => void
}

interface PendingDelete {
  id: string
  name: string
  type: 'live' | 'archived'
}

function SessionDot({ status }: { status: LiveSessionStatus }) {
  if (status.isLoading || status.isAutoRunning) {
    return <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse flex-shrink-0" />
  }
  if (status.hasError) {
    return <span className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
  }
  return <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
}

export function SessionPicker({
  liveSessions,
  activeSessionId,
  archivedSessions,
  onSelectLive,
  onNewSession,
  onRestoreArchived,
  onDeleteArchived,
  onDeleteLive,
}: SessionPickerProps) {
  const [open, setOpen] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null)
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

  const totalCount = liveSessions.length + archivedSessions.length
  const activeStatus = liveSessions.find(s => s.id === activeSessionId)

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
      >
        <Clock className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">Sessions</span>
        {activeStatus && (
          <SessionDot status={activeStatus} />
        )}
        {totalCount > 1 && (
          <span className="w-4 h-4 rounded-full bg-primary-100 text-primary-600 text-[10px] flex items-center justify-center font-semibold">
            {totalCount}
          </span>
        )}
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-80 bg-white border border-slate-200 rounded-lg shadow-lg z-50">
          {/* New Session action */}
          <button
            onClick={() => { onNewSession(); setOpen(false) }}
            className="w-full flex items-center gap-2 px-3 py-2.5 text-xs font-medium text-primary-600 hover:bg-primary-50 border-b border-slate-100 transition-colors"
          >
            <FilePlus className="w-3.5 h-3.5" />
            + New Session
          </button>

          {/* Live Sessions */}
          {liveSessions.length > 0 && (
            <>
              <div className="px-3 py-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-50">
                Live Sessions
              </div>
              <div className="max-h-48 overflow-y-auto">
                {liveSessions.map(session => {
                  const isActive = session.id === activeSessionId
                  const canDelete = liveSessions.length > 1
                  return (
                    <div
                      key={session.id}
                      onClick={() => { onSelectLive(session.id); setOpen(false) }}
                      className={`flex items-center gap-2 px-3 py-2.5 cursor-pointer transition-colors border-b border-slate-50 last:border-0 group ${
                        isActive ? 'bg-primary-50' : 'hover:bg-slate-50'
                      }`}
                    >
                      <SessionDot status={session} />
                      <div className="flex-1 min-w-0">
                        <div className={`text-xs font-medium truncate ${isActive ? 'text-primary-700' : 'text-slate-700'}`}>
                          {session.name}
                          {isActive && <span className="ml-1 text-[10px] text-primary-500">(active)</span>}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] text-slate-400">
                            {session.iterationCount} iter{session.iterationCount !== 1 ? 's' : ''}
                          </span>
                          {session.bestReturn !== null && (
                            <span className={`text-[10px] font-medium ${session.bestReturn >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                              {session.bestReturn >= 0 ? '+' : ''}{(session.bestReturn * 100).toFixed(1)}%
                            </span>
                          )}
                          {(session.isLoading || session.isAutoRunning) && (
                            <span className="text-[10px] text-amber-600 font-medium">running</span>
                          )}
                        </div>
                      </div>
                      {canDelete && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setOpen(false)
                            setPendingDelete({ id: session.id, name: session.name, type: 'live' })
                          }}
                          className="p-1 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded opacity-0 group-hover:opacity-100 transition-all"
                          title="Delete session"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>
            </>
          )}

          {/* Archived Sessions */}
          {archivedSessions.length > 0 && (
            <>
              <div className="px-3 py-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider border-t border-slate-100">
                Archived
              </div>
              <div className="max-h-48 overflow-y-auto">
                {archivedSessions.map(session => (
                  <div
                    key={session.id}
                    className="flex items-center gap-2 px-3 py-2.5 hover:bg-slate-50 border-b border-slate-50 last:border-0 cursor-pointer group transition-colors"
                    onClick={() => { onRestoreArchived(session.id); setOpen(false) }}
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
                        setOpen(false)
                        setPendingDelete({ id: session.id, name: session.name, type: 'archived' })
                      }}
                      className="p-1 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded opacity-0 group-hover:opacity-100 transition-all"
                      title="Delete session"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
      {pendingDelete && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setPendingDelete(null)}
          />
          <div className="relative bg-white rounded-xl shadow-xl p-5 w-72 mx-4">
            <h3 className="text-sm font-semibold text-slate-800 mb-1">Delete session?</h3>
            <p className="text-xs text-slate-500 mb-4 leading-relaxed">
              <span className="font-medium text-slate-700">"{pendingDelete.name}"</span> will be
              permanently deleted. This cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setPendingDelete(null)}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (pendingDelete.type === 'live') {
                    onDeleteLive(pendingDelete.id)
                  } else {
                    onDeleteArchived(pendingDelete.id)
                  }
                  setPendingDelete(null)
                }}
                className="px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
