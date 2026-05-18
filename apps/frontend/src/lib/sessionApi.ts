/**
 * API client for file-based session persistence.
 * Replaces localStorage calls with HTTP calls to /api/sessions.
 */

const API_BASE = import.meta.env.VITE_API_URL || ''

export interface SessionTab {
  id: string
  name: string
  lastAccessedAt: number
}

export interface ArchivedSessionHeader {
  id: string
  name: string
  createdAt: string
  iterationCount: number
  bestReturn: number | null
}

interface SessionMetaSave {
  backtestParams: object
  selectedIterationId: string | null
}

async function apiFetch(url: string, options?: RequestInit): Promise<Response> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`API ${options?.method ?? 'GET'} ${url} failed: ${res.status} ${text}`)
  }
  return res
}

// =============================================================================
// Session Tabs (_index.json)
// =============================================================================

export async function fetchSessionTabs(): Promise<SessionTab[]> {
  try {
    const res = await apiFetch('/api/sessions')
    const data = await res.json()
    return Array.isArray(data.tabs) ? data.tabs : []
  } catch (e) {
    console.warn('[sessionApi] fetchSessionTabs failed:', e)
    return []
  }
}

export async function saveSessionTabs(tabs: SessionTab[]): Promise<void> {
  try {
    await apiFetch('/api/sessions/index', {
      method: 'PUT',
      body: JSON.stringify({ tabs }),
    })
  } catch (e) {
    console.warn('[sessionApi] saveSessionTabs failed:', e)
  }
}

// =============================================================================
// Session Data
// =============================================================================

export async function loadSession(sessionId: string): Promise<object | null> {
  try {
    const res = await apiFetch(`/api/sessions/${sessionId}`)
    return await res.json()
  } catch {
    return null
  }
}

export async function saveSessionMeta(
  sessionId: string,
  meta: SessionMetaSave
): Promise<void> {
  try {
    await apiFetch(`/api/sessions/${sessionId}/meta`, {
      method: 'PUT',
      body: JSON.stringify(meta),
    })
  } catch (e) {
    console.warn('[sessionApi] saveSessionMeta failed:', e)
  }
}

export async function appendActivityEntries(
  sessionId: string,
  entries: object[]
): Promise<void> {
  if (entries.length === 0) return
  try {
    await apiFetch(`/api/sessions/${sessionId}/activity`, {
      method: 'POST',
      body: JSON.stringify({ entries }),
    })
  } catch (e) {
    console.warn('[sessionApi] appendActivityEntries failed:', e)
  }
}

export async function rewriteActivityLog(
  sessionId: string,
  entries: object[]
): Promise<void> {
  try {
    await apiFetch(`/api/sessions/${sessionId}/activity`, {
      method: 'PUT',
      body: JSON.stringify({ entries }),
    })
  } catch (e) {
    console.warn('[sessionApi] rewriteActivityLog failed:', e)
  }
}

export async function upsertIteration(
  sessionId: string,
  index: number,
  node: object
): Promise<void> {
  try {
    await apiFetch(`/api/sessions/${sessionId}/iterations`, {
      method: 'POST',
      body: JSON.stringify({ index, node }),
    })
  } catch (e) {
    console.warn('[sessionApi] upsertIteration failed:', e)
  }
}

/**
 * Lazy-load a single full iteration node (result, rating, insights, scriptCode,
 * prompt) from the per-iteration endpoint. The session list/open path
 * (loadSession) returns a LIGHTWEIGHT list with no heavy payloads; this is the
 * on-demand sibling used when a run is selected.
 *
 * Throws on HTTP/network failure so the caller can surface an explicit error
 * state (the detail pane must not silently blank out).
 */
export async function fetchIterationDetail(
  sessionId: string,
  iterationId: string
): Promise<Record<string, unknown>> {
  const res = await apiFetch(
    `/api/sessions/${sessionId}/iterations/${iterationId}`
  )
  return (await res.json()) as Record<string, unknown>
}

export async function deleteIterationFromStore(
  sessionId: string,
  iterationId: string
): Promise<void> {
  try {
    await apiFetch(`/api/sessions/${sessionId}/iterations/${iterationId}`, {
      method: 'DELETE',
    })
  } catch (e) {
    console.warn('[sessionApi] deleteIterationFromStore failed:', e)
  }
}

export async function deleteSessionFromStore(sessionId: string): Promise<void> {
  try {
    await apiFetch(`/api/sessions/${sessionId}`, { method: 'DELETE' })
  } catch (e) {
    console.warn('[sessionApi] deleteSessionFromStore failed:', e)
  }
}

// =============================================================================
// Archive
// =============================================================================

export async function fetchArchive(): Promise<ArchivedSessionHeader[]> {
  try {
    const res = await apiFetch('/api/sessions/archive')
    const data = await res.json()
    return Array.isArray(data.archive) ? data.archive : []
  } catch (e) {
    console.warn('[sessionApi] fetchArchive failed:', e)
    return []
  }
}

export async function archiveSession(
  sessionId: string,
  archiveMeta: object
): Promise<string> {
  const res = await apiFetch(`/api/sessions/${sessionId}/archive`, {
    method: 'POST',
    body: JSON.stringify({ archiveMeta }),
  })
  const data = await res.json()
  return data.archiveId as string
}

export async function restoreArchivedSession(
  archiveId: string,
  newSessionId: string
): Promise<void> {
  await apiFetch(`/api/sessions/archive/${archiveId}/restore`, {
    method: 'POST',
    body: JSON.stringify({ newSessionId }),
  })
}

export async function deleteArchivedSession(archiveId: string): Promise<void> {
  try {
    await apiFetch(`/api/sessions/archive/${archiveId}`, { method: 'DELETE' })
  } catch (e) {
    console.warn('[sessionApi] deleteArchivedSession failed:', e)
  }
}

export async function importSessionToBackend(
  sessionId: string,
  sessionData: object
): Promise<void> {
  await apiFetch(`/api/sessions/${sessionId}`, {
    method: 'POST',
    body: JSON.stringify({ sessionData }),
  })
}

export async function importArchiveToBackend(
  archiveMeta: object,
  sessionData: object
): Promise<void> {
  await apiFetch('/api/sessions/archive', {
    method: 'POST',
    body: JSON.stringify({ archiveMeta, sessionData }),
  })
}

// =============================================================================
// Beacon (fire-and-forget on page unload)
// =============================================================================

export function beaconSaveSession(
  sessionId: string,
  meta: SessionMetaSave
): void {
  const url = `${API_BASE}/api/sessions/${sessionId}/meta`
  const blob = new Blob([JSON.stringify(meta)], { type: 'application/json' })
  if (navigator.sendBeacon) {
    navigator.sendBeacon(url, blob)
  }
}
