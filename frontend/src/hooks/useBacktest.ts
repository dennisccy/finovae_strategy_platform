import { useState, useCallback, useRef, useEffect, useMemo } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_URL || '';
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

/** Downsample an array to at most `maxLen` evenly-spaced entries. */
function downsample<T>(arr: T[], maxLen: number): T[] {
  if (arr.length <= maxLen) return arr
  const step = arr.length / maxLen
  return Array.from({ length: maxLen }, (_, i) => arr[Math.round(i * step)])
}

/** Trim session data before writing to localStorage to stay under quota. */
function trimForStorage(data: SessionData): SessionData {
  return {
    ...data,
    iterationHistory: data.iterationHistory.map(n => ({
      ...n,
      result: n.result ? {
        ...n.result,
        equity_curve: downsample(n.result.equity_curve, 300),
        trades: n.result.trades.slice(-200),
      } : null,
      timeframeResults: n.timeframeResults.map(tf => ({
        ...tf,
        result: tf.result ? {
          ...tf.result,
          equity_curve: downsample(tf.result.equity_curve, 300),
          trades: tf.result.trades.slice(-200),
        } : null,
      })),
    })),
    activityLog: data.activityLog.slice(-150),
  }
}

function migrateSession(data: SessionData): SessionData {
  // Migrate old timeframe: string → timeframes: string[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const params = data.backtestParams as any
  if ('timeframe' in params && !('timeframes' in params)) {
    params.timeframes = [params.timeframe as string]
    delete params.timeframe
  }
  // Ensure timeframes is always a non-empty string[]
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
    if (!('maxDrawdown' in node)) {
      node.maxDrawdown = node.result?.max_drawdown ?? 0
    }
    return n
  })
  return data
}

function loadSession(sessionId: string): SessionData | null {
  try {
    const key = `finovae_session_${sessionId}`
    const raw = localStorage.getItem(key)
    if (!raw) return null
    const data = JSON.parse(raw) as SessionData
    if (!data.iterationHistory || !data.activityLog || !data.backtestParams) return null
    return migrateSession(data)
  } catch {
    return null
  }
}

function saveSession(sessionId: string, data: SessionData): void {
  const key = `finovae_session_${sessionId}`
  try {
    localStorage.setItem(key, JSON.stringify(trimForStorage(data)))
  } catch (e) {
    if (e instanceof DOMException && e.name === 'QuotaExceededError') {
      console.warn('[session] localStorage quota exceeded — session not saved')
    }
  }
}

export function loadArchive(): ArchivedSession[] {
  try {
    const raw = localStorage.getItem(ARCHIVE_STORAGE_KEY)
    if (!raw) return []
    return JSON.parse(raw) as ArchivedSession[]
  } catch {
    return []
  }
}

export function saveArchive(archive: ArchivedSession[]): void {
  try {
    localStorage.setItem(ARCHIVE_STORAGE_KEY, JSON.stringify(archive))
  } catch (e) {
    if (e instanceof DOMException && e.name === 'QuotaExceededError') {
      console.warn('[session] localStorage quota exceeded — archive not saved')
    }
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

export type ActivityEntryType = 'user-prompt' | 'ai-step' | 'code-preview' | 'error' | 'complete' | 'insights' | 'auto-run'

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
  maxDrawdown: number
  changeSummary?: string
  timestamp: string
  status: IterationStatus
  error?: string
  timeframeResults: TimeframeResult[]
  activeTimeframe: string | null
}

export type Phase = 'idle' | 'generating' | 'executing' | 'results'
export type ActivityStep = 'ai-writing' | 'validating' | 'fetching-data' | 'simulating' | 'calculating' | null

// =============================================================================
// Live Session Status (for multi-session UI)
// =============================================================================

export interface LiveSessionStatus {
  id: string
  name: string
  isLoading: boolean
  isAutoRunning: boolean
  iterationCount: number
  bestReturn: number | null
  hasError: boolean
}

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

export function useBacktest(sessionId: string) {
  const [phase, setPhase] = useState<Phase>(() => {
    const saved = loadSession(sessionId)
    if (saved && saved.iterationHistory.some(n => n.status === 'complete')) return 'results'
    return 'idle'
  })
  const [isLoading, setIsLoading] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)
  const pollIntervalsRef = useRef<ReturnType<typeof setInterval>[]>([])
  const [error, setError] = useState<string | null>(null)

  // Auto-run state
  const [isAutoRunning, setIsAutoRunning] = useState(false)
  const [autoRunProgress, setAutoRunProgress] = useState<{ current: number; max: number } | null>(null)
  const autoRunStopRef = useRef(false)

  // Liquidity cache: computed once per symbol/timeframe/period, reused across iterations
  const cachedLiquidityRef = useRef<{
    liquidity: CategoryRating
    capacity_levels: CapacityLevel[]
  } | null>(null)

  // Activity log state — always start empty on page load
  const [activityLog, setActivityLog] = useState<ActivityEntry[]>([])
  const [selectedIterationId, setSelectedIterationId] = useState<string | null>(() => {
    const saved = loadSession(sessionId)
    return saved?.selectedIterationId ?? null
  })
  const [iterationHistory, setIterationHistory] = useState<IterationNode[]>(() => {
    const saved = loadSession(sessionId)
    if (!saved) return []
    return saved.iterationHistory.map(n =>
      (n.status === 'generating' || n.status === 'executing')
        ? { ...n, status: 'error' as const, error: 'Session interrupted' }
        : n
    )
  })

  const iterationHistoryRef = useRef<IterationNode[]>([])
  useEffect(() => { iterationHistoryRef.current = iterationHistory }, [iterationHistory])

  // Backtest params with defaults
  const [backtestParams, setBacktestParams] = useState<BacktestParams>(() => {
    const saved = loadSession(sessionId)
    return saved?.backtestParams ?? DEFAULT_PARAMS
  })

  // Persist session to localStorage — activityLog intentionally excluded (always cleared on reload)
  useEffect(() => {
    saveSession(sessionId, {
      iterationHistory,
      activityLog,
      backtestParams,
      selectedIterationId,
    })
  }, [sessionId, iterationHistory, backtestParams, selectedIterationId])

  // ==========================================================================
  // Session Archive (shared across all sessions)
  // ==========================================================================

  const [archivedSessions, setArchivedSessions] = useState<ArchivedSession[]>(() => loadArchive())

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
    cachedLiquidityRef.current = null
    localStorage.removeItem(`finovae_session_${sessionId}`)
  }, [sessionId])

  const newSession = useCallback(() => {
    archiveCurrentSession()
    resetToDefaults()
  }, [archiveCurrentSession, resetToDefaults])

  const switchSession = useCallback((id: string) => {
    archiveCurrentSession()

    const target = archivedSessions.find(s => s.id === id)
    if (!target) return

    setArchivedSessions(prev => prev.filter(s => s.id !== id))

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
    cachedLiquidityRef.current = null
  }, [archiveCurrentSession, archivedSessions])

  const deleteArchivedSession = useCallback((id: string) => {
    setArchivedSessions(prev => prev.filter(s => s.id !== id))
  }, [])

  // Derived live session status for multi-session UI
  const sessionStatus: LiveSessionStatus = useMemo(() => {
    const completedNodes = iterationHistory.filter(n => n.status === 'complete' && n.result)
    const bestReturn = completedNodes.length > 0
      ? Math.max(...completedNodes.map(n => n.totalReturn))
      : null
    const firstComplete = iterationHistory.find(n => n.status === 'complete')
    const name = firstComplete?.strategyName || `Session`
    return {
      id: sessionId,
      name,
      isLoading,
      isAutoRunning,
      iterationCount: iterationHistory.length,
      bestReturn,
      hasError: iterationHistory.some(n => n.status === 'error'),
    }
  }, [sessionId, isLoading, isAutoRunning, iterationHistory])

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

  /** Cancel the currently running operation. */
  const cancelOperation = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null

    clearAllPolls()

    setPhase('idle')
    setIsLoading(false)

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

  /** Apply real backend timings to step entries. */
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
  // executeSingleTimeframe
  // ==========================================================================

  const executeSingleTimeframe = useCallback(async (
    scriptId: string,
    scriptCode: string,
    timeframe: string,
    iterationId: string,
    signal?: AbortSignal,
    symbolOverride?: string,
  ): Promise<{ result: BacktestResult; rating: StrategyRating | null } | null> => {
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

    const jobId = crypto.randomUUID()

    const donePhases = new Set<string>()
    const startedPhases = new Set<string>()
    const startedSubstepIds = new Set<number>()

    let pollFinished = false

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

      for (let p = 0; p < currentPhaseIdx; p++) {
        const phaseName = phaseOrder[p]
        if (!donePhases.has(phaseName)) {
          donePhases.add(phaseName)
          const now = Date.now()
          updateLogEntry(phaseToStepId[phaseName], { status: 'done', completedAt: now })
        }
      }

      if (currentPhaseIdx >= 0) {
        const currentPhase = phaseOrder[currentPhaseIdx]
        if (!donePhases.has(currentPhase) && !startedPhases.has(currentPhase)) {
          startedPhases.add(currentPhase)
          updateLogEntry(phaseToStepId[currentPhase], { status: 'active', startedAt: Date.now() })
        }
      }

      if (status.phase === 'simulate' && status.sim_total_bars > 0) {
        const pct = Math.round((status.sim_bar / status.sim_total_bars) * 100)
        updateLogEntry(simStepId, {
          status: 'active',
          content: `[${timeframe}] Running simulation... ${pct}%`,
        })
      }

      if (status.phase === 'calculate') {
        const doneUpTo = status.calculate_step_index
        for (let s = 0; s < metricSubStepIds.length; s++) {
          if (s < doneUpTo) {
            updateLogEntry(metricSubStepIds[s], { status: 'done', completedAt: Date.now() })
          } else if (s === doneUpTo && !startedSubstepIds.has(s)) {
            startedSubstepIds.add(s)
            updateLogEntry(metricSubStepIds[s], { status: 'active', startedAt: Date.now() })
          }
        }
      }
    }

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

  // ==========================================================================
  // generateAndExecute
  // ==========================================================================

  const generateAndExecute = useCallback(async (
    prompt: string,
    model: string,
    previousScriptCode?: string,
    previousBacktestMetrics?: Record<string, number> | null,
    overrideSymbol?: string,
    overrideTimeframes?: string[],
    skipInsights?: boolean,
    changeSummary?: string,
  ) => {
    const timeframes = overrideTimeframes ?? backtestParams.timeframes
    setPhase('generating')
    setIsLoading(true)
    setError(null)

    const abortController = new AbortController()
    abortControllerRef.current = abortController
    const { signal } = abortController

    const iterationId = crypto.randomUUID()
    addLogEntry({
      type: 'user-prompt',
      content: prompt,
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
      maxDrawdown: 0,
      changeSummary,
      timestamp: new Date().toISOString(),
      status: 'generating',
      timeframeResults: initialTfResults,
      activeTimeframe: null,
    }
    setIterationHistory(prev => [...prev, newIteration])

    const genStepId = addLogEntry({
      type: 'ai-step',
      content: 'Generating strategy code...',
      status: 'active',
      startedAt: Date.now(),
      iterationId,
    })

    try {
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
        return null
      }

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

      setPhase('executing')

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

      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId ? { ...n, timeframeResults: [...tfResults] } : n
      ))

      if (signal.aborted) return null

      const firstSuccess = tfResults.find(r => r.status === 'complete' && r.result)
      const anySuccess = !!firstSuccess

      if (anySuccess && firstSuccess?.result) {
        const backtestResult = firstSuccess.result

        // Apply liquidity cache: use first iteration's liquidity for all subsequent ones
        let finalRating = firstSuccess.rating
        if (finalRating) {
          if (!cachedLiquidityRef.current) {
            cachedLiquidityRef.current = {
              liquidity: finalRating.liquidity,
              capacity_levels: finalRating.capacity_levels,
            }
          } else {
            finalRating = {
              ...finalRating,
              liquidity: cachedLiquidityRef.current.liquidity,
              capacity_levels: cachedLiquidityRef.current.capacity_levels,
            }
          }
        }

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

        const completedFields = {
          result: backtestResult,
          rating: finalRating,
          totalReturn: backtestResult.total_return,
          winRate: backtestResult.win_rate,
          numTrades: backtestResult.num_trades,
          sharpe: backtestResult.sharpe_ratio,
          maxDrawdown: backtestResult.max_drawdown,
          status: 'complete' as const,
          activeTimeframe: null,
        }
        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId ? { ...n, ...completedFields } : n
        ))
        // Sync the ref immediately so startAutoRun can read the final metrics
        // before React re-renders and the useEffect syncs it.
        iterationHistoryRef.current = iterationHistoryRef.current.map(n =>
          n.id === iterationId ? { ...n, ...completedFields } : n
        )

        setPhase('results')
        setIsLoading(false)

        if (!skipInsights) {
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
        }
        return iterationId
      } else {
        const errMsg = 'All timeframe backtests failed'
        addLogEntry({ type: 'error', content: errMsg, iterationId })
        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId ? { ...n, status: 'error', error: errMsg, activeTimeframe: null } : n
        ))
        setError(errMsg)
        setPhase('idle')
        setIsLoading(false)
        return null
      }
    } catch (err) {
      clearAllPolls()
      if (err instanceof DOMException && err.name === 'AbortError') return null
      const errMsg = err instanceof Error ? err.message : 'Failed to run strategy'
      addLogEntry({ type: 'error', content: errMsg, iterationId })
      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId ? { ...n, status: 'error', error: errMsg } : n
      ))
      setError(errMsg)
      setPhase('idle')
      setIsLoading(false)
      return null
    }
  }, [backtestParams, addLogEntry, updateLogEntry, clearAllPolls, executeSingleTimeframe])

  // ==========================================================================
  // editAndRerun
  // ==========================================================================

  const editAndRerun = useCallback(async (originalIterationId: string, editedCode: string) => {
    const original = iterationHistory.find(n => n.id === originalIterationId)
    if (!original) return

    const timeframes = backtestParams.timeframes

    setPhase('executing')
    setIsLoading(true)
    setError(null)

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
      maxDrawdown: 0,
      timestamp: new Date().toISOString(),
      status: 'executing',
      timeframeResults: initialTfResults,
      activeTimeframe: null,
    }
    setIterationHistory(prev => [...prev, newIteration])

    try {
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

      if (signal.aborted) return

      const firstSuccess = tfResults.find(r => r.status === 'complete' && r.result)

      if (firstSuccess?.result) {
        const backtestResult = firstSuccess.result

        // Apply liquidity cache
        let finalRating = firstSuccess.rating
        if (finalRating && cachedLiquidityRef.current) {
          finalRating = {
            ...finalRating,
            liquidity: cachedLiquidityRef.current.liquidity,
            capacity_levels: cachedLiquidityRef.current.capacity_levels,
          }
        }

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
                rating: finalRating,
                totalReturn: backtestResult.total_return,
                winRate: backtestResult.win_rate,
                numTrades: backtestResult.num_trades,
                sharpe: backtestResult.sharpe_ratio,
                maxDrawdown: backtestResult.max_drawdown,
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
        localStorage.removeItem(`finovae_session_${sessionId}`)
        setPhase('idle')
      }
      return next
    })
    setActivityLog(prev => prev.filter(e => e.iterationId !== id))
    if (selectedIterationId === id) {
      setSelectedIterationId(null)
    }
  }, [sessionId, selectedIterationId])

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

  const generateInsightsForIteration = useCallback(async (iterationId: string, model: string) => {
    const iteration = iterationHistoryRef.current.find(n => n.id === iterationId)
    if (!iteration?.result) return

    const firstSuccessfulTf = iteration.timeframeResults.find(r => r.status === 'complete')
    const timeframe = firstSuccessfulTf?.timeframe ?? backtestParams.timeframes[0]

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
          backtest_result: iteration.result,
          strategy_name: iteration.strategyName,
          strategy_description: '',
          script_code: iteration.scriptCode,
          model,
          natural_language_prompt: iteration.prompt,
          symbol: backtestParams.symbol,
          timeframe,
          start_date: backtestParams.start_date,
          end_date: backtestParams.end_date,
        }),
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
        // Sync ref immediately so startAutoRun can read the new suggestions
        // on the very next loop iteration (before React re-renders).
        iterationHistoryRef.current = iterationHistoryRef.current.map(n =>
          n.id === iterationId ? { ...n, insights: newInsights } : n
        )
      } else {
        updateLogEntry(insightsStepId, { status: 'done', completedAt: Date.now() })
      }
    } catch {
      updateLogEntry(insightsStepId, { status: 'done', completedAt: Date.now() })
    }
  }, [backtestParams, addLogEntry, updateLogEntry])

  const startAutoRun = useCallback(async (maxAttempts: number, model: string) => {
    const baseline = [...iterationHistoryRef.current]
      .reverse()
      .find(n => n.status === 'complete' && (n.insights?.suggestions?.length ?? 0) > 0)
    if (!baseline) return

    autoRunStopRef.current = false
    setIsAutoRunning(true)
    setAutoRunProgress({ current: 0, max: maxAttempts })

    let baselineId = baseline.id
    let suggestionIndex = 0
    let attempt = 0

    while (attempt < maxAttempts && !autoRunStopRef.current) {
      const currentBaseline = iterationHistoryRef.current.find(n => n.id === baselineId)
      const suggestions = currentBaseline?.insights?.suggestions ?? []
      if (suggestionIndex >= suggestions.length) break

      const suggestion = suggestions[suggestionIndex]
      const baselineScore = (currentBaseline?.numTrades ?? 0) > 0
        ? (currentBaseline?.totalReturn ?? -Infinity)
        : -Infinity

      addLogEntry({ type: 'auto-run', content: `Trying "${suggestion.title}"...` })

      const baselineResult = currentBaseline?.result
      const metrics = baselineResult ? {
        total_return: baselineResult.total_return,
        max_drawdown: baselineResult.max_drawdown,
        num_trades: baselineResult.num_trades,
        win_rate: baselineResult.win_rate,
        sharpe_ratio: baselineResult.sharpe_ratio,
        profit_factor: baselineResult.profit_factor,
      } : null

      let newId: string | null = null
      try {
        newId = await generateAndExecute(
          suggestion.prompt, model, currentBaseline?.scriptCode, metrics,
          undefined, undefined, true, suggestion.title,
        )
      } catch {
        // AbortError from stopAutoRun — fall through to stop-flag check
      }

      if (autoRunStopRef.current) {
        if (newId) deleteIteration(newId)
        break
      }

      if (newId) {
        const newIteration = iterationHistoryRef.current.find(n => n.id === newId)
        const newScore = (newIteration?.numTrades ?? 0) > 0 ? (newIteration?.totalReturn ?? -Infinity) : -Infinity
        const fmt = (v: number) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(2)}%`

        if (newIteration?.status === 'complete' && newScore > baselineScore) {
          attempt++
          setAutoRunProgress({ current: attempt, max: maxAttempts })
          addLogEntry({ type: 'auto-run', content: `Kept (${attempt}/${maxAttempts}): ${fmt(newScore)} > ${fmt(baselineScore)} — generating suggestions...` })
          baselineId = newId
          suggestionIndex = 0
          await generateInsightsForIteration(newId, model)
        } else {
          const discardNumTrades = newIteration?.numTrades ?? 0
          const discardRet    = discardNumTrades === 0 ? '—' : fmt(newIteration?.totalReturn ?? 0)
          const discardDd     = `${((newIteration?.maxDrawdown ?? 0) * 100).toFixed(1)}%`
          const discardSr     = (newIteration?.sharpe ?? 0).toFixed(2)
          const discardWr     = `${((newIteration?.winRate ?? 0) * 100).toFixed(0)}%`
          const discardReason = discardNumTrades === 0
            ? 'no trades'
            : newScore === baselineScore
              ? `same return as baseline (${fmt(baselineScore)})`
              : `return below baseline (${fmt(baselineScore)})`
          addLogEntry({
            type: 'auto-run',
            content: `Discarded: Ret ${discardRet} | DD ${discardDd} | SR ${discardSr} | WR ${discardWr} — ${discardReason}, trying next`,
          })
          deleteIteration(newId)
          suggestionIndex++
        }
      } else {
        suggestionIndex++
      }
    }

    setIsAutoRunning(false)
    setAutoRunProgress(null)
    autoRunStopRef.current = false

    const reason = attempt >= maxAttempts ? `${maxAttempts} improvements done` : 'no more suggestions'
    addLogEntry({ type: 'auto-run', content: `Auto Run finished — ${reason}` })
  }, [generateAndExecute, deleteIteration, addLogEntry, generateInsightsForIteration])

  const stopAutoRun = useCallback(() => {
    autoRunStopRef.current = true
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    clearAllPolls()
    setPhase('idle')
    setIsLoading(false)
    setIterationHistory(prev => prev.filter(n => n.status !== 'generating' && n.status !== 'executing'))
    setActivityLog(prev => prev.map(e =>
      (e.status === 'active' || e.status === 'pending')
        ? { ...e, status: 'done' as const, completedAt: Date.now() }
        : e
    ))
  }, [clearAllPolls])

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
    isAutoRunning,
    autoRunProgress,
    startAutoRun,
    stopAutoRun,
    sessionStatus,
  }
}
