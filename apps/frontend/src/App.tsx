import { useState, useCallback, useEffect, useRef } from 'react'
import { SessionContainer } from './components/SessionContainer'
import { getModels, defaultModelId, FALLBACK_MODEL, type ModelOption } from './lib/modelsApi'
import { SessionPicker } from './components/SessionPicker'
import { MessageSquare, GitBranch } from 'lucide-react'
import { type LiveSessionStatus, type ArchivedSession } from './hooks/useBacktest'
import {
  fetchSessionTabs,
  saveSessionTabs,
  fetchArchive,
  restoreArchivedSession,
  deleteArchivedSession,
  deleteSessionFromStore,
  importSessionToBackend,
  importArchiveToBackend,
  type SessionTab,
} from './lib/sessionApi'

const OLD_SESSION_TABS_KEY = 'finovae_session_tabs'
const OLD_ARCHIVE_KEY = 'finovae_sessions_archive'
const MIGRATION_FLAG = 'finovae_migrated_v1'

async function runMigration(): Promise<void> {
  if (localStorage.getItem(MIGRATION_FLAG)) return

  const oldTabsRaw = localStorage.getItem(OLD_SESSION_TABS_KEY)
  if (!oldTabsRaw) {
    localStorage.setItem(MIGRATION_FLAG, '1')
    return
  }

  try {
    const oldTabs = JSON.parse(oldTabsRaw) as SessionTab[]

    // Migrate live sessions
    for (const tab of oldTabs) {
      const raw = localStorage.getItem(`finovae_session_${tab.id}`)
      if (raw) {
        try {
          await importSessionToBackend(tab.id, JSON.parse(raw))
        } catch (e) {
          console.warn('[migration] failed to import session', tab.id, e)
        }
      }
    }

    // Migrate archive
    const archiveRaw = localStorage.getItem(OLD_ARCHIVE_KEY)
    if (archiveRaw) {
      const archive = JSON.parse(archiveRaw) as Array<{
        id: string; name: string; createdAt: string
        iterationCount: number; bestReturn: number | null
        data: object
      }>
      for (const entry of archive) {
        try {
          const { data, ...meta } = entry
          await importArchiveToBackend(meta, data)
        } catch (e) {
          console.warn('[migration] failed to import archive entry', entry.id, e)
        }
      }
    }

    // Upload the tabs index
    await saveSessionTabs(oldTabs)

    // Clear old localStorage
    oldTabs.forEach(tab => localStorage.removeItem(`finovae_session_${tab.id}`))
    localStorage.removeItem(OLD_SESSION_TABS_KEY)
    localStorage.removeItem(OLD_ARCHIVE_KEY)

    console.info('[migration] Migrated', oldTabs.length, 'sessions from localStorage to backend')
  } catch (e) {
    console.warn('[migration] Migration failed:', e)
  }

  localStorage.setItem(MIGRATION_FLAG, '1')
}

function App() {
  const [liveSessions, setLiveSessions] = useState<SessionTab[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string>('')
  const [liveStatuses, setLiveStatuses] = useState<Record<string, LiveSessionStatus>>({})
  const [mobileTab, setMobileTab] = useState<'activity' | 'iterations'>('activity')
  const [lastUsedModel, setLastUsedModel] = useState(FALLBACK_MODEL)
  const [availableModels, setAvailableModels] = useState<ModelOption[]>([])
  const [tabsLoaded, setTabsLoaded] = useState(false)

  // Archive state managed at App level
  const [archivedSessions, setArchivedSessions] = useState<ArchivedSession[]>([])

  // Debounce ref for saving tabs
  const tabsSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Fetch the model list once — single source of truth is backend /api/models
  // (apps/backend/shared/model_catalog.py). No hardcoded model ids here.
  useEffect(() => {
    let cancelled = false
    getModels().then(models => {
      if (cancelled) return
      setAvailableModels(models)
      setLastUsedModel(prev => (prev === FALLBACK_MODEL ? defaultModelId(models) : prev))
    })
    return () => {
      cancelled = true
    }
  }, [])

  // Load tabs + archive from backend on mount (with migration)
  useEffect(() => {
    (async () => {
      await runMigration()

      const [tabs, archive] = await Promise.all([fetchSessionTabs(), fetchArchive()])

      if (tabs.length > 0) {
        const sorted = [...tabs].sort((a, b) => b.lastAccessedAt - a.lastAccessedAt)
        setLiveSessions(sorted)
        setActiveSessionId(sorted[0].id)
      } else {
        const newId = crypto.randomUUID()
        const initial: SessionTab[] = [{ id: newId, name: 'Session 1', lastAccessedAt: Date.now() }]
        setLiveSessions(initial)
        setActiveSessionId(newId)
        await saveSessionTabs(initial)
      }

      setArchivedSessions(archive as ArchivedSession[])
      setTabsLoaded(true)
    })()
  }, [])

  // Persist live session tabs whenever they change (debounced 1s)
  useEffect(() => {
    if (!tabsLoaded) return
    if (tabsSaveTimerRef.current) clearTimeout(tabsSaveTimerRef.current)
    const snapshot = liveSessions
    tabsSaveTimerRef.current = setTimeout(() => {
      saveSessionTabs(snapshot)
    }, 1000)
  }, [tabsLoaded, liveSessions])

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
    setLiveSessions(prev => prev.map(s => s.id === id ? { ...s, lastAccessedAt: Date.now() } : s))
    setActiveSessionId(id)
  }, [])

  const handleRestoreArchived = useCallback(async (archivedId: string) => {
    const session = archivedSessions.find(s => s.id === archivedId)
    if (!session) return
    const newId = crypto.randomUUID()
    try {
      await restoreArchivedSession(archivedId, newId)
    } catch (e) {
      console.warn('[App] restoreArchivedSession failed:', e)
    }
    setLiveSessions(prev => [...prev, { id: newId, name: session.name, lastAccessedAt: Date.now() }])
    setActiveSessionId(newId)
    setArchivedSessions(prev => prev.filter(s => s.id !== archivedId))
  }, [archivedSessions])

  const handleDeleteArchived = useCallback(async (id: string) => {
    setArchivedSessions(prev => prev.filter(s => s.id !== id))
    await deleteArchivedSession(id)
  }, [])

  const handleDeleteLive = useCallback(async (id: string) => {
    setLiveSessions(prev => {
      const next = prev.filter(s => s.id !== id)
      setActiveSessionId(cur => {
        if (cur === id) {
          const fallback = next[0]
          return fallback?.id ?? cur
        }
        return cur
      })
      return next
    })
    await deleteSessionFromStore(id)
  }, [])

  // Build LiveSessionStatus list for SessionPicker
  const liveSessionStatuses: LiveSessionStatus[] = liveSessions.map(s => {
    const status = liveStatuses[s.id]
    return status ?? {
      id: s.id,
      name: s.name,
      isLoading: false,
      isAutoRunning: false,
      isFetchingSession: true,
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
              isLoading={!tabsLoaded}
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
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-colors ${mobileTab === 'activity'
            ? 'text-primary-600 border-b-2 border-primary-600'
            : 'text-slate-500'
            }`}
        >
          <MessageSquare className="w-4 h-4" />
          Activity
        </button>
        <button
          onClick={() => setMobileTab('iterations')}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-colors ${mobileTab === 'iterations'
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
          availableModels={availableModels}
          onLastUsedModelChange={setLastUsedModel}
          onStatusChange={handleStatusChange}
          onNameChange={(name) => handleNameChange(session.id, name)}
        />
      ))}
    </div>
  )
}

export default App
