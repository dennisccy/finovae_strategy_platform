import { useState, useCallback, useRef, useEffect } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_URL || '';
const SESSION_STORAGE_KEY = 'finovae_session';
const ARCHIVE_STORAGE_KEY = 'finovae_sessions_archive';

// =============================================================================
// Session Persistence Helpers
// =============================================================================

interface SessionData {
  iterationHistory: IterationNode[]
  activityLog: ActivityEntry[]
  backtestParams: BacktestParams
  selectedIterationId: string | null
}

export interface ArchivedSession {
  id: string
  name: string
  createdAt: string
  iterationCount: number
  bestReturn: number | null
  data: SessionData
}

function migrateSession(data: SessionData): SessionData {
  // Migrate old timeframe: string → timeframes: string[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const params = data.backtestParams as any
  if ('timeframe' in params && !('timeframes' in params)) {
    params.timeframes = [params.timeframe as string]
    delete params.timeframe
  }
  // Ensure timeframes is always a non-empty string[] (guard against string corruption)
  if (!Array.isArray(params.timeframes) || params.timeframes.length === 0) {
    params.timeframes = typeof params.timeframes === 'string' && params.timeframes
      ? [params.timeframes as string]
      : ['4h']
  }
  // Migrate old iterations: add timeframeResults + activeTimeframe
  data.iterationHistory = data.iterationHistory.map(n => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const node = n as any
    if (!('timeframeResults' in node)) {
      node.timeframeResults = []
      node.activeTimeframe = null
    }
    return n
  })
  return data
}

function loadSession(): SessionData | null {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as SessionData
    if (!data.iterationHistory || !data.activityLog || !data.backtestParams) return null
    return migrateSession(data)
  } catch {
    return null
  }
}

function saveSession(data: SessionData): void {
  try {
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(data))
  } catch {
    // quota exceeded — silently ignore
  }
}

function loadArchive(): ArchivedSession[] {
  try {
    const raw = localStorage.getItem(ARCHIVE_STORAGE_KEY)
    if (!raw) return []
    return JSON.parse(raw) as ArchivedSession[]
  } catch {
    return []
  }
}

function saveArchive(archive: ArchivedSession[]): void {
  try {
    localStorage.setItem(ARCHIVE_STORAGE_KEY, JSON.stringify(archive))
  } catch {
    // quota exceeded — silently ignore
  }
}

function deriveSessionName(data: SessionData): string {
  const firstComplete = data.iterationHistory.find(n => n.status === 'complete')
  if (firstComplete?.strategyName) return firstComplete.strategyName

  const firstPrompt = data.iterationHistory[0]?.prompt
  if (firstPrompt) return firstPrompt.length > 40 ? firstPrompt.slice(0, 40) + '...' : firstPrompt

  return `Session ${new Date().toLocaleDateString()}`
}

// =============================================================================
// Core Types
// =============================================================================

export interface Trade {
  trade_id: string
  entry_time: string
  exit_time: string
  entry_price: number
  exit_price: number
  quantity: number
  pnl: number
  pnl_percent: number
  commission_paid: number
}

export interface EquityPoint {
  timestamp: string
  equity: number
  drawdown: number
}

export interface BacktestResult {
  run_id: string
  total_return: number
  max_drawdown: number
  num_trades: number
  win_rate: number
  sharpe_ratio: number
  profit_factor: number
  equity_curve: EquityPoint[]
  trades: Trade[]
}

export interface Condition {
  left_operand: string
  operator: string
  right_operand: string | number
}

export interface IndicatorConfig {
  name: string
  params: Record<string, number>
  output_name: string
}

export interface StrategySpec {
  name: string
  description: string
  entry_conditions: Condition[]
  exit_conditions: Condition[]
  position_size: {
    type: string
    value: number
  }
  indicators: IndicatorConfig[]
}

export interface BacktestRequest {
  natural_language: string
  symbol: string
  timeframe: string
  start_date: string
  end_date: string
  initial_capital: number
  model: string
}

export interface RunHistoryItem {
  run_id: string
  timestamp: string
  natural_language: string
  total_return: number
  num_trades: number
}

export interface GeneratedScript {
  script_id: string
  script_code: string
  strategy_name: string
  strategy_description: string
  validation_errors: string[]
}

// =============================================================================
// Strategy Rating Types
// =============================================================================

export interface DrawdownPeriod {
  start_time: string
  end_time: string
  recovery_time: string | null
  depth: number
  duration_days: number
  recovery_days: number | null
}

export interface TradeExcursion {
  trade_id: string
  pnl_percent: number
  mae: number
  mfe: number
}

export interface MonthlyReturn {
  year: number
  month: number
  return_pct: number
}

export interface RollingMetric {
  timestamp: string
  value: number
}

export interface HistogramBin {
  bin_start: number
  bin_end: number
  count: number
}

export interface SimulatedStopLevel {
  level_pct: number
  adjusted_return: number
  adjusted_win_rate: number
  trades_affected: number
}

export interface CapacityLevel {
  capital: number
  volume_participation_pct: number
  estimated_slippage_bps: number
}

export interface CategoryRating {
  name: string
  label: string
  stars: number
  key_metrics: Record<string, number | string>
  analyses: Record<string, unknown>
}

export interface StrategyRating {
  profitability: CategoryRating
  risk_resistance: CategoryRating
  risk_reward: CategoryRating
  win_rate_ev: CategoryRating
  liquidity: CategoryRating
  benchmark_equity: EquityPoint[]
  benchmark_total_return: number
  monthly_returns: MonthlyReturn[]
  trade_excursions: TradeExcursion[]
  drawdown_periods: DrawdownPeriod[]
  rolling_sharpe: RollingMetric[]
  rolling_sharpe_benchmark: RollingMetric[]
  return_distribution: HistogramBin[]
  simulated_stops: SimulatedStopLevel[]
  simulated_take_profits: SimulatedStopLevel[]
  capacity_levels: CapacityLevel[]
  annual_returns: Record<number, number>
  benchmark_annual_returns: Record<number, number>
}

export interface InsightsSuggestion {
  title: string
  description: string
  prompt: string
}

export interface StrategyInsights {
  summary: string
  suggestions: InsightsSuggestion[]
}

// =============================================================================
// New Studio Layout Types
// =============================================================================

export type ActivityEntryType = 'user-prompt' | 'ai-step' | 'code-preview' | 'error' | 'complete' | 'insights'

export interface ActivityEntry {
  id: string
  type: ActivityEntryType
  timestamp: string
  content: string
  detail?: string
  status?: 'pending' | 'active' | 'done' | 'error'
  startedAt?: number
  completedAt?: number
  substep?: boolean
  iterationId?: string
}

const METRIC_SUBSTEPS = [
  'Computing buy-and-hold benchmark',
  'Calculating monthly and annual returns',
  'Measuring per-trade risk (MAE/MFE)',
  'Analyzing drawdown periods',
  'Computing rolling Sharpe ratios',
  'Building return distribution',
  'Computing risk-adjusted ratios (alpha, Sortino, VaR)',
  'Simulating stop-loss scenarios',
  'Simulating take-profit scenarios',
  'Estimating liquidity and capacity',
] as const

/** Maps backend calculate_steps keys (in order) to METRIC_SUBSTEPS indices. */
const CALCULATE_STEP_KEYS = [
  'benchmark_ms',
  'returns_ms',
  'mae_mfe_ms',
  'drawdowns_ms',
  'rolling_sharpe_ms',
  'distribution_ms',
  'ratios_ms',
  'sim_stops_ms',
  'sim_tp_ms',
  'liquidity_ms',
] as const

export interface BacktestParams {
  symbol: string
  timeframes: string[]
  start_date: string
  end_date: string
  initial_capital: number
}

export type TimeframeStatus = 'pending' | 'running' | 'complete' | 'error'

export interface TimeframeResult {
  timeframe: string
  status: TimeframeStatus
  result: BacktestResult | null
  rating: StrategyRating | null
  error?: string
}

export type IterationStatus = 'generating' | 'executing' | 'complete' | 'error'

export interface IterationNode {
  id: string
  prompt: string
  scriptCode: string
  scriptId: string
  strategyName: string
  result: BacktestResult | null
  rating: StrategyRating | null
  insights: StrategyInsights | null
  totalReturn: number
  winRate: number
  numTrades: number
  sharpe: number
  timestamp: string
  status: IterationStatus
  error?: string
  timeframeResults: TimeframeResult[]
  activeTimeframe: string | null
}

export type Phase = 'idle' | 'generating' | 'executing' | 'results'
export type ActivityStep = 'ai-writing' | 'validating' | 'fetching-data' | 'simulating' | 'calculating' | null

// =============================================================================
// Hook
// =============================================================================

const DEFAULT_PARAMS: BacktestParams = {
  symbol: 'SOLUSDT',
  timeframes: ['4h'],
  start_date: '2024-01-01',
  end_date: new Date().toISOString().split('T')[0],
  initial_capital: 10000,
}

export function useBacktest() {
  const [phase, setPhase] = useState<Phase>(() => {
    const saved = loadSession()
    if (saved && saved.iterationHistory.some(n => n.status === 'complete')) return 'results'
    return 'idle'
  })
  const [isLoading, setIsLoading] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)
  const pollIntervalsRef = useRef<ReturnType<typeof setInterval>[]>([])
  const [error, setError] = useState<string | null>(null)

  // Activity log state — always start empty on page load
  // (Restored only when explicitly switching sessions via switchSession)
  const [activityLog, setActivityLog] = useState<ActivityEntry[]>([])
  const [selectedIterationId, setSelectedIterationId] = useState<string | null>(() => {
    const saved = loadSession()
    return saved?.selectedIterationId ?? null
  })
  const [iterationHistory, setIterationHistory] = useState<IterationNode[]>(() => {
    const saved = loadSession()
    if (!saved) return []
    // Mark any generating/executing iterations as error (interrupted session)
    return saved.iterationHistory.map(n =>
      (n.status === 'generating' || n.status === 'executing')
        ? { ...n, status: 'error' as const, error: 'Session interrupted' }
        : n
    )
  })

  // Backtest params with defaults
  const [backtestParams, setBacktestParams] = useState<BacktestParams>(() => {
    const saved = loadSession()
    return saved?.backtestParams ?? DEFAULT_PARAMS
  })

  // Persist session to localStorage on meaningful state changes
  useEffect(() => {
    saveSession({
      iterationHistory,
      activityLog,
      backtestParams,
      selectedIterationId,
    })
  }, [iterationHistory, activityLog, backtestParams, selectedIterationId])

  // ==========================================================================
  // Session Archive
  // ==========================================================================

  const [archivedSessions, setArchivedSessions] = useState<ArchivedSession[]>(() => loadArchive())

  // Persist archive to localStorage
  useEffect(() => {
    saveArchive(archivedSessions)
  }, [archivedSessions])

  const archiveCurrentSession = useCallback((): void => {
    if (iterationHistory.length === 0) return

    const snapshot: SessionData = {
      iterationHistory,
      activityLog,
      backtestParams,
      selectedIterationId,
    }

    const completedReturns = iterationHistory
      .filter(n => n.status === 'complete' && n.result)
      .map(n => n.totalReturn)

    const archived: ArchivedSession = {
      id: crypto.randomUUID(),
      name: deriveSessionName(snapshot),
      createdAt: new Date().toISOString(),
      iterationCount: iterationHistory.length,
      bestReturn: completedReturns.length > 0 ? Math.max(...completedReturns) : null,
      data: snapshot,
    }

    setArchivedSessions(prev => [archived, ...prev])
  }, [iterationHistory, activityLog, backtestParams, selectedIterationId])

  const resetToDefaults = useCallback(() => {
    setIterationHistory([])
    setActivityLog([])
    setBacktestParams(DEFAULT_PARAMS)
    setSelectedIterationId(null)
    setPhase('idle')
    setError(null)
    setIsLoading(false)
    localStorage.removeItem(SESSION_STORAGE_KEY)
  }, [])

  const newSession = useCallback(() => {
    archiveCurrentSession()
    resetToDefaults()
  }, [archiveCurrentSession, resetToDefaults])

  const switchSession = useCallback((id: string) => {
    // Archive current if non-empty
    archiveCurrentSession()

    // Find target in archive
    const target = archivedSessions.find(s => s.id === id)
    if (!target) return

    // Remove target from archive
    setArchivedSessions(prev => prev.filter(s => s.id !== id))

    // Restore with interrupted-state cleanup (same as initial load)
    const data = migrateSession(target.data)
    setActivityLog(
      data.activityLog.map(e =>
        (e.status === 'active' || e.status === 'pending')
          ? { ...e, status: 'done' as const, completedAt: e.completedAt ?? Date.now() }
          : e
      )
    )
    setIterationHistory(
      data.iterationHistory.map(n =>
        (n.status === 'generating' || n.status === 'executing')
          ? { ...n, status: 'error' as const, error: 'Session interrupted' }
          : n
      )
    )
    setBacktestParams(data.backtestParams)
    setSelectedIterationId(data.selectedIterationId)
    setPhase(data.iterationHistory.some(n => n.status === 'complete') ? 'results' : 'idle')
    setError(null)
    setIsLoading(false)
  }, [archiveCurrentSession, archivedSessions])

  const deleteArchivedSession = useCallback((id: string) => {
    setArchivedSessions(prev => prev.filter(s => s.id !== id))
  }, [])

  const addLogEntry = useCallback((entry: Omit<ActivityEntry, 'id' | 'timestamp'>) => {
    const newEntry: ActivityEntry = {
      ...entry,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
    }
    setActivityLog(prev => [...prev, newEntry])
    return newEntry.id
  }, [])

  const updateLogEntry = useCallback((id: string, updates: Partial<ActivityEntry>) => {
    setActivityLog(prev => prev.map(e => e.id === id ? { ...e, ...updates } : e))
  }, [])

  /** Clear all active polling intervals. */
  const clearAllPolls = useCallback(() => {
    pollIntervalsRef.current.forEach(clearInterval)
    pollIntervalsRef.current = []
  }, [])

  /** Fetch job status from backend polling endpoint. Returns null on error/404. */
  const fetchJobStatus = useCallback(async (jobId: string): Promise<{
    phase: string
    calculate_step: string | null
    calculate_step_index: number
    sim_bar: number
    sim_total_bars: number
  } | null> => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/job-status/${jobId}`)
      if (!res.ok) return null
      return await res.json()
    } catch {
      return null
    }
  }, [])

  /** Cancel the currently running operation (generate, execute, or edit-and-rerun). */
  const cancelOperation = useCallback(() => {
    // 1. Abort all in-flight fetch requests
    abortControllerRef.current?.abort()
    abortControllerRef.current = null

    // 2. Clear polling intervals
    clearAllPolls()

    // 3. Reset loading state
    setPhase('idle')
    setIsLoading(false)

    // 4. Mark current in-progress iteration as error
    setIterationHistory(prev => prev.map(n => {
      if (n.status === 'generating' || n.status === 'executing') {
        return {
          ...n,
          status: 'error' as const,
          error: 'Cancelled by user',
          activeTimeframe: null,
          timeframeResults: n.timeframeResults.map(tf =>
            tf.status === 'running' || tf.status === 'pending'
              ? { ...tf, status: 'error' as TimeframeStatus, error: 'Cancelled by user' }
              : tf
          ),
        }
      }
      return n
    }))

    // 5. Mark any active/pending log entries as done and add cancellation entry
    setActivityLog(prev => {
      const updated = prev.map(e =>
        (e.status === 'active' || e.status === 'pending')
          ? { ...e, status: 'done' as const, completedAt: Date.now() }
          : e
      )
      const cancelEntry: ActivityEntry = {
        id: crypto.randomUUID(),
        type: 'error',
        timestamp: new Date().toISOString(),
        content: 'Operation cancelled',
      }
      return [...updated, cancelEntry]
    })
  }, [clearAllPolls])

  /** Apply real backend timings to step entries, overwriting any estimated values. */
  const applyRealTimings = useCallback((
    timings: { validate_ms: number; fetch_ms: number; simulate_ms: number; calculate_ms: number; calculate_steps?: Record<string, number> | null } | undefined,
    base: number,
    stepIds: { validate: string; fetch: string; sim: string; calc: string; metrics: string[] },
  ) => {
    if (timings) {
      const validateEnd = base + timings.validate_ms
      const fetchEnd = validateEnd + timings.fetch_ms
      const simEnd = fetchEnd + timings.simulate_ms
      const calcEnd = simEnd + timings.calculate_ms

      updateLogEntry(stepIds.validate, { status: 'done', startedAt: base, completedAt: validateEnd })
      updateLogEntry(stepIds.fetch, { status: 'done', startedAt: validateEnd, completedAt: fetchEnd })
      updateLogEntry(stepIds.sim, { status: 'done', startedAt: fetchEnd, completedAt: simEnd })
      updateLogEntry(stepIds.calc, { status: 'done', startedAt: simEnd, completedAt: calcEnd })

      // Use per-step timings from backend if available, otherwise divide evenly
      const calcSteps = timings.calculate_steps
      if (calcSteps) {
        let cursor = simEnd
        stepIds.metrics.forEach((id, i) => {
          const key = CALCULATE_STEP_KEYS[i]
          const ms = key ? (calcSteps[key] ?? 0) : 0
          updateLogEntry(id, {
            status: 'done',
            startedAt: cursor,
            completedAt: cursor + ms,
          })
          cursor += ms
        })
      } else {
        const metricSlice = timings.calculate_ms / METRIC_SUBSTEPS.length
        stepIds.metrics.forEach((id, i) => {
          updateLogEntry(id, {
            status: 'done',
            startedAt: simEnd + i * metricSlice,
            completedAt: simEnd + (i + 1) * metricSlice,
          })
        })
      }
    } else {
      const now = Date.now()
      updateLogEntry(stepIds.validate, { status: 'done', completedAt: now })
      updateLogEntry(stepIds.fetch, { status: 'done', completedAt: now })
      updateLogEntry(stepIds.sim, { status: 'done', completedAt: now })
      updateLogEntry(stepIds.calc, { status: 'done', completedAt: now })
      stepIds.metrics.forEach(id => updateLogEntry(id, { status: 'done', completedAt: now }))
    }
  }, [updateLogEntry])

  // ==========================================================================
  // generateAndExecute — replaces separate generate + manual execute
  // ==========================================================================

  /** Execute backtest for a single timeframe. Returns the result data or null on failure. */
  const executeSingleTimeframe = useCallback(async (
    scriptId: string,
    scriptCode: string,
    timeframe: string,
    iterationId: string,
    signal?: AbortSignal,
    symbolOverride?: string,
  ): Promise<{ result: BacktestResult; rating: StrategyRating | null } | null> => {
    // Step entries
    const validateStepId = addLogEntry({
      type: 'ai-step', content: `[${timeframe}] Validating code...`, status: 'active', startedAt: Date.now(), iterationId,
    })
    const fetchStepId = addLogEntry({
      type: 'ai-step', content: `[${timeframe}] Fetching market data...`, status: 'pending', iterationId,
    })
    const simStepId = addLogEntry({
      type: 'ai-step', content: `[${timeframe}] Running simulation...`, status: 'pending', iterationId,
    })
    const calcStepId = addLogEntry({
      type: 'ai-step', content: `[${timeframe}] Calculating metrics...`, status: 'pending', iterationId,
    })
    const metricSubStepIds = METRIC_SUBSTEPS.map(label =>
      addLogEntry({
        type: 'ai-step', content: `[${timeframe}] ${label}`, status: 'pending', substep: true, iterationId,
      })
    )

    const stepIds = { validate: validateStepId, fetch: fetchStepId, sim: simStepId, calc: calcStepId, metrics: metricSubStepIds }
    const executionStartTime = Date.now()

    // Generate job ID for polling
    const jobId = crypto.randomUUID()

    // Track which phases we've already marked done / started (to avoid redundant updates)
    const donePhases = new Set<string>()
    const startedPhases = new Set<string>()   // guards startedAt — only set once per phase
    const startedSubstepIds = new Set<number>() // guards startedAt — only set once per substep index

    // Prevents late in-flight poll callbacks from overriding applyRealTimings results
    let pollFinished = false

    // Phase-to-log-entry mapping for polling updates
    const phaseOrder = ['validate', 'fetch', 'simulate', 'calculate'] as const
    const phaseToStepId: Record<string, string> = {
      validate: validateStepId,
      fetch: fetchStepId,
      simulate: simStepId,
      calculate: calcStepId,
    }

    const applyPolledStatus = (status: {
      phase: string
      calculate_step_index: number
      sim_bar: number
      sim_total_bars: number
    }) => {
      const currentPhaseIdx = phaseOrder.indexOf(status.phase as typeof phaseOrder[number])

      // Mark all phases before current as done
      for (let p = 0; p < currentPhaseIdx; p++) {
        const phaseName = phaseOrder[p]
        if (!donePhases.has(phaseName)) {
          donePhases.add(phaseName)
          const now = Date.now()
          updateLogEntry(phaseToStepId[phaseName], { status: 'done', completedAt: now })
        }
      }

      // Mark current phase as active — set startedAt ONLY the first time we see this phase
      if (currentPhaseIdx >= 0) {
        const currentPhase = phaseOrder[currentPhaseIdx]
        if (!donePhases.has(currentPhase) && !startedPhases.has(currentPhase)) {
          startedPhases.add(currentPhase)
          updateLogEntry(phaseToStepId[currentPhase], { status: 'active', startedAt: Date.now() })
        }
      }

      // For simulate phase: update progress % in content (do NOT reset startedAt)
      if (status.phase === 'simulate' && status.sim_total_bars > 0) {
        const pct = Math.round((status.sim_bar / status.sim_total_bars) * 100)
        updateLogEntry(simStepId, {
          status: 'active',
          content: `[${timeframe}] Running simulation... ${pct}%`,
        })
      }

      // For calculate phase: update substep progress
      // Note: calcStepId is already handled by the generic phase handler above — no duplicate update
      if (status.phase === 'calculate') {
        const doneUpTo = status.calculate_step_index
        for (let s = 0; s < metricSubStepIds.length; s++) {
          if (s < doneUpTo) {
            // Always update done steps (safe to re-set completedAt)
            updateLogEntry(metricSubStepIds[s], { status: 'done', completedAt: Date.now() })
          } else if (s === doneUpTo && !startedSubstepIds.has(s)) {
            // Only set startedAt once for the currently active substep
            startedSubstepIds.add(s)
            updateLogEntry(metricSubStepIds[s], { status: 'active', startedAt: Date.now() })
          }
        }
      }
    }

    // Start polling
    const pollId = setInterval(async () => {
      if (pollFinished) return
      const status = await fetchJobStatus(jobId)
      if (!status || pollFinished) return
      applyPolledStatus(status)
    }, 500)
    pollIntervalsRef.current.push(pollId)

    try {
      const execResponse = await fetch(`${API_BASE_URL}/api/execute-backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          script_id: scriptId,
          script_code: scriptCode,
          symbol: symbolOverride ?? backtestParams.symbol,
          timeframe,
          start_date: backtestParams.start_date,
          end_date: backtestParams.end_date,
          initial_capital: backtestParams.initial_capital,
          job_id: jobId,
        }),
        signal,
      })

      const execData = await execResponse.json()
      pollFinished = true
      clearInterval(pollId)
      pollIntervalsRef.current = pollIntervalsRef.current.filter(id => id !== pollId)

      if (!execData.success) {
        const errNow = Date.now()
        updateLogEntry(validateStepId, { status: 'done', completedAt: errNow })
        updateLogEntry(fetchStepId, { status: 'done', completedAt: errNow })
        updateLogEntry(simStepId, { status: 'done', completedAt: errNow })
        updateLogEntry(calcStepId, { status: 'error', completedAt: errNow })
        metricSubStepIds.forEach(id => updateLogEntry(id, { status: 'error', completedAt: errNow }))
        const backendErrors: string[] = execData.errors || []
        const errMsg = backendErrors.length > 0
          ? backendErrors.join('; ')
          : `Backtest failed for ${timeframe}`
        addLogEntry({ type: 'error', content: `[${timeframe}] ${errMsg}`, iterationId })
        return null
      }

      applyRealTimings(execData.timings, executionStartTime, stepIds)
      return {
        result: execData.result as BacktestResult,
        rating: (execData.rating as StrategyRating) || null,
      }
    } catch (err) {
      pollFinished = true
      clearInterval(pollId)
      pollIntervalsRef.current = pollIntervalsRef.current.filter(id => id !== pollId)
      // If aborted, don't mark as error — cancelOperation already handles state
      if (err instanceof DOMException && err.name === 'AbortError') {
        return null
      }
      const errNow = Date.now()
      updateLogEntry(validateStepId, { status: 'done', completedAt: errNow })
      updateLogEntry(fetchStepId, { status: 'done', completedAt: errNow })
      updateLogEntry(simStepId, { status: 'done', completedAt: errNow })
      updateLogEntry(calcStepId, { status: 'error', completedAt: errNow })
      metricSubStepIds.forEach(id => updateLogEntry(id, { status: 'error', completedAt: errNow }))
      return null
    }
  }, [backtestParams, addLogEntry, updateLogEntry, fetchJobStatus, applyRealTimings])

  const generateAndExecute = useCallback(async (
    prompt: string,
    model: string,
    previousScriptCode?: string,
    previousBacktestMetrics?: Record<string, number> | null,
    overrideSymbol?: string,
    overrideTimeframes?: string[],
  ) => {
    const timeframes = overrideTimeframes ?? backtestParams.timeframes
    setPhase('generating')
    setIsLoading(true)
    setError(null)

    // Create AbortController for this operation
    const abortController = new AbortController()
    abortControllerRef.current = abortController
    const { signal } = abortController

    // 1. User prompt entry
    const iterationId = crypto.randomUUID()
    addLogEntry({
      type: 'user-prompt',
      content: prompt,
      iterationId,
    })

    // 2. Create iteration node (generating) with pending timeframeResults
    const initialTfResults: TimeframeResult[] = timeframes.map(tf => ({
      timeframe: tf,
      status: 'pending' as TimeframeStatus,
      result: null,
      rating: null,
    }))

    const newIteration: IterationNode = {
      id: iterationId,
      prompt,
      scriptCode: '',
      scriptId: '',
      strategyName: '',
      result: null,
      rating: null,
      insights: null,
      totalReturn: 0,
      winRate: 0,
      numTrades: 0,
      sharpe: 0,
      timestamp: new Date().toISOString(),
      status: 'generating',
      timeframeResults: initialTfResults,
      activeTimeframe: null,
    }
    setIterationHistory(prev => [...prev, newIteration])

    // 3. AI generating step
    const genStepId = addLogEntry({
      type: 'ai-step',
      content: 'Generating strategy code...',
      status: 'active',
      startedAt: Date.now(),
      iterationId,
    })

    try {
      // 4. POST /api/generate-strategy (once, using first timeframe)
      const body: Record<string, unknown> = {
        natural_language: prompt,
        model,
        symbol: overrideSymbol ?? backtestParams.symbol,
        timeframe: timeframes[0],
        start_date: backtestParams.start_date,
        end_date: backtestParams.end_date,
      }
      if (previousScriptCode) {
        body.previous_script_code = previousScriptCode
      }
      if (previousBacktestMetrics) {
        body.previous_backtest_metrics = previousBacktestMetrics
      }

      const genResponse = await fetch(`${API_BASE_URL}/api/generate-strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal,
      })

      const genData = await genResponse.json()

      if (!genData.success) {
        const errMsg = genData.errors?.join(', ') || 'Strategy generation failed'
        updateLogEntry(genStepId, { status: 'error', completedAt: Date.now() })
        addLogEntry({ type: 'error', content: errMsg, iterationId })
        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId ? { ...n, status: 'error', error: errMsg } : n
        ))
        setError(errMsg)
        setPhase('idle')
        setIsLoading(false)
        return
      }

      // 5. Generation success
      updateLogEntry(genStepId, { status: 'done', completedAt: Date.now() })

      const scriptCode = genData.script_code
      const scriptId = genData.script_id
      const strategyName = genData.strategy_name || 'Strategy'

      addLogEntry({
        type: 'code-preview',
        content: strategyName,
        detail: scriptCode,
        iterationId,
      })

      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId
          ? { ...n, scriptCode, scriptId, strategyName, status: 'executing' }
          : n
      ))

      // 6. Execute across all timeframes in parallel
      setPhase('executing')

      // Mark all TFs as running simultaneously
      const runningTfResults: TimeframeResult[] = timeframes.map(tf => ({
        timeframe: tf,
        status: 'running' as TimeframeStatus,
        result: null,
        rating: null,
      }))
      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId
          ? { ...n, timeframeResults: [...runningTfResults], activeTimeframe: timeframes[0] }
          : n
      ))

      const tfRunnerIds: string[] = []
      timeframes.forEach((tf, i) => {
        tfRunnerIds.push(addLogEntry({
          type: 'ai-step',
          content: `Running ${tf}... (${i + 1}/${timeframes.length})`,
          status: 'active',
          startedAt: Date.now(),
          iterationId,
        }))
      })

      const promises = timeframes.map((tf) =>
        executeSingleTimeframe(scriptId, scriptCode, tf, iterationId, signal, overrideSymbol)
      )
      const settled = await Promise.allSettled(promises)
      const doneNow = Date.now()
      tfRunnerIds.forEach(id => updateLogEntry(id, { status: 'done', completedAt: doneNow }))

      // Build final TF results from settled promises
      const tfResults: TimeframeResult[] = timeframes.map((tf, i) => {
        const outcome = settled[i]
        if (outcome.status === 'fulfilled' && outcome.value) {
          return {
            timeframe: tf,
            status: 'complete' as TimeframeStatus,
            result: outcome.value.result,
            rating: outcome.value.rating,
          }
        } else {
          // Check if this was an abort
          if (signal.aborted) {
            return {
              timeframe: tf,
              status: 'error' as TimeframeStatus,
              result: null,
              rating: null,
              error: 'Cancelled by user',
            }
          }
          const errMsg = outcome.status === 'rejected'
            ? (outcome.reason?.message || `Backtest failed for ${tf}`)
            : `Backtest failed for ${tf}`
          return {
            timeframe: tf,
            status: 'error' as TimeframeStatus,
            result: null,
            rating: null,
            error: errMsg,
          }
        }
      })

      // Update iteration with final TF results
      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId ? { ...n, timeframeResults: [...tfResults] } : n
      ))

      // If aborted, return early (cancelOperation already cleaned up state)
      if (signal.aborted) return

      // 7. All timeframes done — set top-level result from first successful TF
      const firstSuccess = tfResults.find(r => r.status === 'complete' && r.result)
      const anySuccess = !!firstSuccess

      if (anySuccess && firstSuccess?.result) {
        const backtestResult = firstSuccess.result

        const returnPct = (backtestResult.total_return * 100).toFixed(2)
        const returnSign = backtestResult.total_return >= 0 ? '+' : ''
        const tfSummaries = tfResults
          .filter(r => r.status === 'complete' && r.result)
          .map(r => `${r.timeframe}: ${r.result!.total_return >= 0 ? '+' : ''}${(r.result!.total_return * 100).toFixed(2)}%`)
          .join(', ')
        addLogEntry({
          type: 'complete',
          content: timeframes.length > 1
            ? `Results: ${tfSummaries}`
            : `${returnSign}${returnPct}% return, ${backtestResult.num_trades} trades, ${(backtestResult.win_rate * 100).toFixed(0)}% win rate, ${backtestResult.sharpe_ratio.toFixed(2)} sharpe`,
          iterationId,
        })

        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId
            ? {
                ...n,
                result: backtestResult,
                rating: firstSuccess.rating,
                totalReturn: backtestResult.total_return,
                winRate: backtestResult.win_rate,
                numTrades: backtestResult.num_trades,
                sharpe: backtestResult.sharpe_ratio,
                status: 'complete',
                activeTimeframe: null,
              }
            : n
        ))

        setPhase('results')
        setIsLoading(false)

        // 8. Auto-generate insights using first successful result
        const insightsStepId = addLogEntry({
          type: 'ai-step',
          content: 'Generating suggestions...',
          status: 'active',
          startedAt: Date.now(),
          iterationId,
        })

        try {
          const insResponse = await fetch(`${API_BASE_URL}/api/generate-insights`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              backtest_result: backtestResult,
              strategy_name: strategyName,
              strategy_description: genData.strategy_description || '',
              script_code: scriptCode,
              model: model,
              natural_language_prompt: prompt,
              symbol: overrideSymbol ?? backtestParams.symbol,
              timeframe: firstSuccess.timeframe,
              start_date: backtestParams.start_date,
              end_date: backtestParams.end_date,
            }),
            signal,
          })

          const insData = await insResponse.json()

          if (insData.success) {
            const newInsights: StrategyInsights = {
              summary: insData.summary || '',
              suggestions: insData.suggestions || [],
            }

            updateLogEntry(insightsStepId, { status: 'done', completedAt: Date.now() })

            addLogEntry({
              type: 'insights',
              content: newInsights.summary,
              detail: JSON.stringify(newInsights.suggestions),
              iterationId,
            })

            setIterationHistory(prev => prev.map(n =>
              n.id === iterationId ? { ...n, insights: newInsights } : n
            ))
          } else {
            updateLogEntry(insightsStepId, { status: 'done', completedAt: Date.now() })
          }
        } catch {
          updateLogEntry(insightsStepId, { status: 'done', completedAt: Date.now() })
        }
      } else {
        // All timeframes failed
        const errMsg = 'All timeframe backtests failed'
        addLogEntry({ type: 'error', content: errMsg, iterationId })
        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId ? { ...n, status: 'error', error: errMsg, activeTimeframe: null } : n
        ))
        setError(errMsg)
        setPhase('idle')
        setIsLoading(false)
      }
    } catch (err) {
      clearAllPolls()
      // If aborted, return early — cancelOperation already handled state
      if (err instanceof DOMException && err.name === 'AbortError') return
      const errMsg = err instanceof Error ? err.message : 'Failed to run strategy'
      addLogEntry({ type: 'error', content: errMsg, iterationId })
      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId ? { ...n, status: 'error', error: errMsg } : n
      ))
      setError(errMsg)
      setPhase('idle')
      setIsLoading(false)
    }
  }, [backtestParams, addLogEntry, updateLogEntry, clearAllPolls, executeSingleTimeframe])

  // ==========================================================================
  // editAndRerun — execute with edited script code (skip generation)
  // ==========================================================================

  const editAndRerun = useCallback(async (originalIterationId: string, editedCode: string) => {
    const original = iterationHistory.find(n => n.id === originalIterationId)
    if (!original) return

    const timeframes = backtestParams.timeframes

    setPhase('executing')
    setIsLoading(true)
    setError(null)

    // Create AbortController for this operation
    const abortController = new AbortController()
    abortControllerRef.current = abortController
    const { signal } = abortController

    const iterationId = crypto.randomUUID()

    addLogEntry({
      type: 'user-prompt',
      content: `Re-running "${original.strategyName}" with edited code`,
      iterationId,
    })

    addLogEntry({
      type: 'code-preview',
      content: original.strategyName + ' (edited)',
      detail: editedCode,
      iterationId,
    })

    const initialTfResults: TimeframeResult[] = timeframes.map(tf => ({
      timeframe: tf,
      status: 'pending' as TimeframeStatus,
      result: null,
      rating: null,
    }))

    const newIteration: IterationNode = {
      id: iterationId,
      prompt: original.prompt + ' (edited)',
      scriptCode: editedCode,
      scriptId: original.scriptId,
      strategyName: original.strategyName + ' (edited)',
      result: null,
      rating: null,
      insights: null,
      totalReturn: 0,
      winRate: 0,
      numTrades: 0,
      sharpe: 0,
      timestamp: new Date().toISOString(),
      status: 'executing',
      timeframeResults: initialTfResults,
      activeTimeframe: null,
    }
    setIterationHistory(prev => [...prev, newIteration])

    try {
      // Mark all TFs as running simultaneously
      const runningTfResults: TimeframeResult[] = timeframes.map(tf => ({
        timeframe: tf,
        status: 'running' as TimeframeStatus,
        result: null,
        rating: null,
      }))
      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId
          ? { ...n, timeframeResults: [...runningTfResults], activeTimeframe: timeframes[0] }
          : n
      ))

      const tfRunnerIds: string[] = []
      timeframes.forEach((tf, i) => {
        tfRunnerIds.push(addLogEntry({
          type: 'ai-step',
          content: `Running ${tf}... (${i + 1}/${timeframes.length})`,
          status: 'active',
          startedAt: Date.now(),
          iterationId,
        }))
      })

      const promises = timeframes.map((tf) =>
        executeSingleTimeframe(original.scriptId, editedCode, tf, iterationId, signal)
      )
      const settled = await Promise.allSettled(promises)
      const doneNow = Date.now()
      tfRunnerIds.forEach(id => updateLogEntry(id, { status: 'done', completedAt: doneNow }))

      // Build final TF results from settled promises
      const tfResults: TimeframeResult[] = timeframes.map((tf, i) => {
        const outcome = settled[i]
        if (outcome.status === 'fulfilled' && outcome.value) {
          return {
            timeframe: tf,
            status: 'complete' as TimeframeStatus,
            result: outcome.value.result,
            rating: outcome.value.rating,
          }
        } else {
          if (signal.aborted) {
            return {
              timeframe: tf,
              status: 'error' as TimeframeStatus,
              result: null,
              rating: null,
              error: 'Cancelled by user',
            }
          }
          return {
            timeframe: tf,
            status: 'error' as TimeframeStatus,
            result: null,
            rating: null,
            error: `Backtest failed for ${tf}`,
          }
        }
      })

      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId ? { ...n, timeframeResults: [...tfResults] } : n
      ))

      // If aborted, return early
      if (signal.aborted) return

      const firstSuccess = tfResults.find(r => r.status === 'complete' && r.result)

      if (firstSuccess?.result) {
        const backtestResult = firstSuccess.result
        const returnPct = (backtestResult.total_return * 100).toFixed(2)
        const returnSign = backtestResult.total_return >= 0 ? '+' : ''
        const tfSummaries = tfResults
          .filter(r => r.status === 'complete' && r.result)
          .map(r => `${r.timeframe}: ${r.result!.total_return >= 0 ? '+' : ''}${(r.result!.total_return * 100).toFixed(2)}%`)
          .join(', ')
        addLogEntry({
          type: 'complete',
          content: timeframes.length > 1
            ? `Results: ${tfSummaries}`
            : `${returnSign}${returnPct}% return, ${backtestResult.num_trades} trades, ${(backtestResult.win_rate * 100).toFixed(0)}% win rate, ${backtestResult.sharpe_ratio.toFixed(2)} sharpe`,
          iterationId,
        })

        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId
            ? {
                ...n,
                result: backtestResult,
                rating: firstSuccess.rating,
                totalReturn: backtestResult.total_return,
                winRate: backtestResult.win_rate,
                numTrades: backtestResult.num_trades,
                sharpe: backtestResult.sharpe_ratio,
                status: 'complete',
                activeTimeframe: null,
              }
            : n
        ))

        setPhase('results')
        setIsLoading(false)
      } else {
        const errMsg = 'All timeframe backtests failed'
        addLogEntry({ type: 'error', content: errMsg, iterationId })
        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId ? { ...n, status: 'error', error: errMsg, activeTimeframe: null } : n
        ))
        setError(errMsg)
        setPhase('idle')
        setIsLoading(false)
      }
    } catch (err) {
      clearAllPolls()
      if (err instanceof DOMException && err.name === 'AbortError') return
      const errMsg = err instanceof Error ? err.message : 'Failed to execute backtest'
      addLogEntry({ type: 'error', content: errMsg, iterationId })
      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId ? { ...n, status: 'error', error: errMsg } : n
      ))
      setError(errMsg)
      setPhase('idle')
      setIsLoading(false)
    }
  }, [iterationHistory, backtestParams, addLogEntry, clearAllPolls, executeSingleTimeframe])

  // ==========================================================================
  // deleteIteration
  // ==========================================================================

  const deleteIteration = useCallback((id: string) => {
    setIterationHistory(prev => {
      const next = prev.filter(n => n.id !== id)
      if (next.length === 0) {
        localStorage.removeItem(SESSION_STORAGE_KEY)
        setPhase('idle')
      }
      return next
    })
    setActivityLog(prev => prev.filter(e => e.iterationId !== id))
    if (selectedIterationId === id) {
      setSelectedIterationId(null)
    }
  }, [selectedIterationId])

  // ==========================================================================
  // selectIteration
  // ==========================================================================

  const selectIteration = useCallback((id: string | null) => {
    setSelectedIterationId(id)
  }, [])

  // ==========================================================================
  // resetToIdle
  // ==========================================================================

  const resetToIdle = useCallback(() => {
    setPhase('idle')
    setError(null)
  }, [])

  return {
    phase,
    isLoading,
    error,
    backtestParams,
    setBacktestParams,
    activityLog,
    selectedIterationId,
    iterationHistory,
    generateAndExecute,
    editAndRerun,
    cancelOperation,
    deleteIteration,
    selectIteration,
    resetToIdle,
    archivedSessions,
    newSession,
    switchSession,
    deleteArchivedSession,
  }
}
