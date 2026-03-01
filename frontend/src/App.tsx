import { useState, useCallback, useEffect } from 'react'
import { SessionContainer } from './components/SessionContainer'
import { SessionPicker } from './components/SessionPicker'
import { MessageSquare, GitBranch } from 'lucide-react'
import { loadArchive, saveArchive, type ArchivedSession, type LiveSessionStatus } from './hooks/useBacktest'

const SESSION_TABS_KEY = 'finovae_session_tabs'

interface SessionTab {
  id: string
  name: string
  lastAccessedAt: number
}

function loadLiveSessionTabs(): SessionTab[] {
  try {
    const tabs = localStorage.getItem(SESSION_TABS_KEY)
    if (tabs) {
      const parsed = JSON.parse(tabs) as SessionTab[]
      if (Array.isArray(parsed) && parsed.length > 0) {
        // Ensure all sessions have lastAccessedAt (migration)
        return parsed.map(s => ({
          ...s,
          lastAccessedAt: s.lastAccessedAt ?? Date.now()
        }))
      }
    }

    // Migration: old single-session format
    const oldSession = localStorage.getItem('finovae_session')
    if (oldSession) {
      const newId = crypto.randomUUID()
      localStorage.setItem(`finovae_session_${newId}`, oldSession)
      localStorage.removeItem('finovae_session')
      return [{ id: newId, name: 'Session 1', lastAccessedAt: Date.now() }]
    }

    // Fresh start
    return [{ id: crypto.randomUUID(), name: 'Session 1', lastAccessedAt: Date.now() }]
  } catch {
    return [{ id: crypto.randomUUID(), name: 'Session 1', lastAccessedAt: Date.now() }]
  }
}

function saveLiveSessionTabs(tabs: SessionTab[]): void {
  try {
    localStorage.setItem(SESSION_TABS_KEY, JSON.stringify(tabs))
  } catch {
    // ignore
  }
}

function getLatestSessionId(sessions: SessionTab[]): string {
  if (sessions.length === 0) return ''
  // Find session with most recent lastAccessedAt
  return sessions.reduce((latest, current) =>
    current.lastAccessedAt > latest.lastAccessedAt ? current : latest
  ).id
}

function App() {
  const [liveSessions, setLiveSessions] = useState<SessionTab[]>(loadLiveSessionTabs)
  const [activeSessionId, setActiveSessionId] = useState<string>(() => getLatestSessionId(liveSessions))
  const [liveStatuses, setLiveStatuses] = useState<Record<string, LiveSessionStatus>>({})
  const [mobileTab, setMobileTab] = useState<'activity' | 'iterations'>('activity')
  const [lastUsedModel, setLastUsedModel] = useState('claude-sonnet-4-6')

  // Archive state managed at App level (shared across sessions)
  const [archivedSessions, setArchivedSessions] = useState<ArchivedSession[]>(() => loadArchive())

  // Persist live session tabs whenever they change
  useEffect(() => {
    saveLiveSessionTabs(liveSessions)
  }, [liveSessions])

  // Persist archive changes
  useEffect(() => {
    saveArchive(archivedSessions)
  }, [archivedSessions])

  // Keep session names in sync with strategy names
  const handleNameChange = useCallback((sessionId: string, name: string) => {
    setLiveSessions(prev => prev.map(s => s.id === sessionId ? { ...s, name } : s))
  }, [])

  const handleStatusChange = useCallback((status: LiveSessionStatus) => {
    setLiveStatuses(prev => ({ ...prev, [status.id]: status }))
  }, [])

  const handleNewSession = useCallback(() => {
    const n = liveSessions.length + 1
    const newId = crypto.randomUUID()
    const newSession: SessionTab = { id: newId, name: `Session ${n}`, lastAccessedAt: Date.now() }
    setLiveSessions(prev => [...prev, newSession])
    setActiveSessionId(newId)
  }, [liveSessions.length])

  const handleSelectLive = useCallback((id: string) => {
    // Update lastAccessedAt when session is selected
    setLiveSessions(prev => prev.map(s => s.id === id ? { ...s, lastAccessedAt: Date.now() } : s))
    setActiveSessionId(id)
  }, [])

  const handleRestoreArchived = useCallback((archivedId: string) => {
    const session = archivedSessions.find(s => s.id === archivedId)
    if (!session) return

    // Write the archived session data to the new session's localStorage key
    const newId = crypto.randomUUID()
    try {
      localStorage.setItem(`finovae_session_${newId}`, JSON.stringify(session.data))
    } catch {
      // ignore quota issues
    }

    // Add as a new live session with current timestamp
    setLiveSessions(prev => [...prev, { id: newId, name: session.name, lastAccessedAt: Date.now() }])
    setActiveSessionId(newId)

    // Remove from archive
    setArchivedSessions(prev => prev.filter(s => s.id !== archivedId))
  }, [archivedSessions])

  const handleDeleteArchived = useCallback((id: string) => {
    setArchivedSessions(prev => prev.filter(s => s.id !== id))
  }, [])

  const handleDeleteLive = useCallback((id: string) => {
    setLiveSessions(prev => {
      const next = prev.filter(s => s.id !== id)
      // Switch active session if the deleted one was active
      setActiveSessionId(cur => {
        if (cur === id) {
          const fallback = next.find(s => s.id !== id) ?? next[0]
          return fallback?.id ?? cur
        }
        return cur
      })
      return next
    })
    // Remove localStorage data for the deleted session
    try { localStorage.removeItem(`finovae_session_${id}`) } catch { /* ignore */ }
  }, [])

  // Build the list of LiveSessionStatus objects for SessionPicker
  const liveSessionStatuses: LiveSessionStatus[] = liveSessions.map(s => {
    const status = liveStatuses[s.id]
    return status ?? {
      id: s.id,
      name: s.name,
      isLoading: false,
      isAutoRunning: false,
      iterationCount: 0,
      bestReturn: null,
      hasError: false,
    }
  })

  const activeIterationCount = liveStatuses[activeSessionId]?.iterationCount ?? 0

  return (
    <div className="h-screen bg-slate-50 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-4 py-3 lg:px-6 lg:py-4">
        <div className="flex items-center justify-between max-w-screen-2xl mx-auto">
          <div className="flex items-center gap-2 lg:gap-3 min-w-0">
            <div className="w-7 h-7 lg:w-8 lg:h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-white font-bold text-xs lg:text-sm">F</span>
            </div>
            <h1 className="text-base lg:text-xl font-semibold text-slate-800 truncate">
              Finovae Strategy Platform
            </h1>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0 ml-2">
            <SessionPicker
              liveSessions={liveSessionStatuses}
              activeSessionId={activeSessionId}
              archivedSessions={archivedSessions}
              onSelectLive={handleSelectLive}
              onNewSession={handleNewSession}
              onRestoreArchived={handleRestoreArchived}
              onDeleteArchived={handleDeleteArchived}
              onDeleteLive={handleDeleteLive}
            />
            <span className="text-xs lg:text-sm text-slate-500">v0.3.0</span>
          </div>
        </div>
      </header>

      {/* Mobile Tab Bar */}
      <div className="lg:hidden flex border-b border-slate-200 bg-white">
        <button
          onClick={() => setMobileTab('activity')}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-colors ${
            mobileTab === 'activity'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Activity
        </button>
        <button
          onClick={() => setMobileTab('iterations')}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-colors ${
            mobileTab === 'iterations'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500'
          }`}
        >
          <GitBranch className="w-4 h-4" />
          Iterations
          {activeIterationCount > 0 && (
            <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-600 text-xs flex items-center justify-center font-semibold">
              {activeIterationCount}
            </span>
          )}
        </button>
      </div>

      {/* Session containers — all mounted, only active one visible */}
      {liveSessions.map(session => (
        <SessionContainer
          key={session.id}
          sessionId={session.id}
          sessionName={session.name}
          isActive={session.id === activeSessionId}
          mobileTab={mobileTab}
          lastUsedModel={lastUsedModel}
          onLastUsedModelChange={setLastUsedModel}
          onStatusChange={handleStatusChange}
          onNameChange={(name) => handleNameChange(session.id, name)}
        />
      ))}
    </div>
  )
}

export default App
