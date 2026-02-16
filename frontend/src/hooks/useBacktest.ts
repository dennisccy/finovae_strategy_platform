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

function loadSession(): SessionData | null {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as SessionData
    if (!data.iterationHistory || !data.activityLog || !data.backtestParams) return null
    return data
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
  'Comparing against buy-and-hold benchmark',
  'Analyzing returns and drawdown periods',
  'Measuring per-trade risk (MAE/MFE)',
  'Computing Sharpe, Sortino, and risk ratios',
  'Simulating stop-loss and take-profit scenarios',
  'Estimating liquidity and capacity',
] as const

export interface BacktestParams {
  symbol: string
  timeframe: string
  start_date: string
  end_date: string
  initial_capital: number
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
}

export type Phase = 'idle' | 'generating' | 'executing' | 'results'
export type ActivityStep = 'ai-writing' | 'validating' | 'fetching-data' | 'simulating' | 'calculating' | null

// =============================================================================
// Hook
// =============================================================================

const DEFAULT_PARAMS: BacktestParams = {
  symbol: 'BTCUSDT',
  timeframe: '4h',
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
  const progressTimersRef = useRef<ReturnType<typeof setTimeout>[]>([])
  const [error, setError] = useState<string | null>(null)

  // Activity log state — restore from localStorage with cleanup
  const [activityLog, setActivityLog] = useState<ActivityEntry[]>(() => {
    const saved = loadSession()
    if (!saved) return []
    // Mark any active/pending steps as done (interrupted session)
    return saved.activityLog.map(e =>
      (e.status === 'active' || e.status === 'pending')
        ? { ...e, status: 'done' as const, completedAt: e.completedAt ?? Date.now() }
        : e
    )
  })
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
    const data = target.data
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

  /** Start estimated progress animation for execution steps. Returns cleanup fn. */
  const startProgressTimers = useCallback((
    stepIds: { validate: string; fetch: string; sim: string; calc: string; metrics: string[] },
  ) => {
    // Clear any previous timers
    progressTimersRef.current.forEach(clearTimeout)
    progressTimersRef.current = []

    const t1 = setTimeout(() => {
      updateLogEntry(stepIds.validate, { status: 'done', completedAt: Date.now() })
      updateLogEntry(stepIds.fetch, { status: 'active', startedAt: Date.now() })
    }, 1500)
    const t2 = setTimeout(() => {
      updateLogEntry(stepIds.fetch, { status: 'done', completedAt: Date.now() })
      updateLogEntry(stepIds.sim, { status: 'active', startedAt: Date.now() })
    }, 4000)
    const t3 = setTimeout(() => {
      updateLogEntry(stepIds.sim, { status: 'done', completedAt: Date.now() })
      updateLogEntry(stepIds.calc, { status: 'active', startedAt: Date.now() })
      updateLogEntry(stepIds.metrics[0], { status: 'active', startedAt: Date.now() })
    }, 8000)
    const metricTimers = stepIds.metrics.slice(1).map((id, i) =>
      setTimeout(() => {
        const now = Date.now()
        updateLogEntry(stepIds.metrics[i], { status: 'done', completedAt: now })
        updateLogEntry(id, { status: 'active', startedAt: now })
      }, 8000 + (i + 1) * 1200)
    )
    progressTimersRef.current = [t1, t2, t3, ...metricTimers]
  }, [updateLogEntry])

  const clearProgressTimers = useCallback(() => {
    progressTimersRef.current.forEach(clearTimeout)
    progressTimersRef.current = []
  }, [])

  /** Apply real backend timings to step entries, overwriting any estimated values. */
  const applyRealTimings = useCallback((
    timings: { validate_ms: number; fetch_ms: number; simulate_ms: number; calculate_ms: number } | undefined,
    base: number,
    stepIds: { validate: string; fetch: string; sim: string; calc: string; metrics: string[] },
  ) => {
    if (timings) {
      const validateEnd = base + timings.validate_ms
      const fetchEnd = validateEnd + timings.fetch_ms
      const simEnd = fetchEnd + timings.simulate_ms
      const calcEnd = simEnd + timings.calculate_ms
      const metricSlice = timings.calculate_ms / METRIC_SUBSTEPS.length

      updateLogEntry(stepIds.validate, { status: 'done', startedAt: base, completedAt: validateEnd })
      updateLogEntry(stepIds.fetch, { status: 'done', startedAt: validateEnd, completedAt: fetchEnd })
      updateLogEntry(stepIds.sim, { status: 'done', startedAt: fetchEnd, completedAt: simEnd })
      updateLogEntry(stepIds.calc, { status: 'done', startedAt: simEnd, completedAt: calcEnd })
      stepIds.metrics.forEach((id, i) => {
        updateLogEntry(id, {
          status: 'done',
          startedAt: simEnd + i * metricSlice,
          completedAt: simEnd + (i + 1) * metricSlice,
        })
      })
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

  const generateAndExecute = useCallback(async (
    prompt: string,
    model: string,
    previousScriptCode?: string,
    previousBacktestMetrics?: Record<string, number> | null,
  ) => {
    setPhase('generating')
    setIsLoading(true)
    setError(null)

    // 1. User prompt entry
    const iterationId = crypto.randomUUID()
    addLogEntry({
      type: 'user-prompt',
      content: prompt,
      iterationId,
    })

    // 2. Create iteration node (generating)
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
      // 4. POST /api/generate-strategy
      const body: Record<string, unknown> = {
        natural_language: prompt,
        model,
        symbol: backtestParams.symbol,
        timeframe: backtestParams.timeframe,
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

      // Add code preview entry
      addLogEntry({
        type: 'code-preview',
        content: strategyName,
        detail: scriptCode,
        iterationId,
      })

      // Update iteration with script info
      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId
          ? { ...n, scriptCode, scriptId, strategyName, status: 'executing' }
          : n
      ))

      // 6. Auto-execute
      setPhase('executing')

      // Step entries (all pending except first)
      const validateStepId = addLogEntry({
        type: 'ai-step', content: 'Validating code...', status: 'active', startedAt: Date.now(), iterationId,
      })
      const fetchStepId = addLogEntry({
        type: 'ai-step', content: 'Fetching market data...', status: 'pending', iterationId,
      })
      const simStepId = addLogEntry({
        type: 'ai-step', content: 'Running simulation...', status: 'pending', iterationId,
      })
      const calcStepId = addLogEntry({
        type: 'ai-step', content: 'Calculating metrics...', status: 'pending', iterationId,
      })
      const metricSubStepIds = METRIC_SUBSTEPS.map(label =>
        addLogEntry({
          type: 'ai-step', content: label, status: 'pending', substep: true, iterationId,
        })
      )

      const stepIds = { validate: validateStepId, fetch: fetchStepId, sim: simStepId, calc: calcStepId, metrics: metricSubStepIds }
      const executionStartTime = Date.now()

      // Animate estimated progress while API call is in-flight
      startProgressTimers(stepIds)

      // 7. POST /api/execute-backtest
      const execResponse = await fetch(`${API_BASE_URL}/api/execute-backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          script_id: scriptId,
          script_code: scriptCode,
          symbol: backtestParams.symbol,
          timeframe: backtestParams.timeframe,
          start_date: backtestParams.start_date,
          end_date: backtestParams.end_date,
          initial_capital: backtestParams.initial_capital,
        }),
      })

      const execData = await execResponse.json()

      // Stop estimated timers — real timings will overwrite
      clearProgressTimers()

      if (!execData.success) {
        const errMsg = execData.errors?.join(', ') || 'Backtest execution failed'
        const errNow = Date.now()
        updateLogEntry(validateStepId, { status: 'done', completedAt: errNow })
        updateLogEntry(fetchStepId, { status: 'done', completedAt: errNow })
        updateLogEntry(simStepId, { status: 'done', completedAt: errNow })
        updateLogEntry(calcStepId, { status: 'error', completedAt: errNow })
        metricSubStepIds.forEach(id => updateLogEntry(id, { status: 'error', completedAt: errNow }))
        addLogEntry({ type: 'error', content: errMsg, iterationId })
        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId ? { ...n, status: 'error', error: errMsg } : n
        ))
        setError(errMsg)
        setPhase('idle')
        setIsLoading(false)
        return
      }

      // 8. Execution success — overwrite with real backend timings
      applyRealTimings(execData.timings, executionStartTime, stepIds)

      const backtestResult: BacktestResult = execData.result
      const resultRating: StrategyRating | null = execData.rating || null

      // Complete entry
      const returnPct = (backtestResult.total_return * 100).toFixed(2)
      const returnSign = backtestResult.total_return >= 0 ? '+' : ''
      addLogEntry({
        type: 'complete',
        content: `${returnSign}${returnPct}% return, ${backtestResult.num_trades} trades, ${(backtestResult.win_rate * 100).toFixed(0)}% win rate, ${backtestResult.sharpe_ratio.toFixed(2)} sharpe`,
        iterationId,
      })

      // Update iteration
      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId
          ? {
              ...n,
              result: backtestResult,
              rating: resultRating,
              totalReturn: backtestResult.total_return,
              winRate: backtestResult.win_rate,
              numTrades: backtestResult.num_trades,
              sharpe: backtestResult.sharpe_ratio,
              status: 'complete',
            }
          : n
      ))

      setPhase('results')
      setIsLoading(false)

      // 9. Auto-generate insights
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
            model: 'claude-haiku-4-5-20251001',
            symbol: backtestParams.symbol,
            timeframe: backtestParams.timeframe,
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

          // Add insights log entry with clickable suggestions (store full JSON)
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
    } catch (err) {
      clearProgressTimers()
      const errMsg = err instanceof Error ? err.message : 'Failed to run strategy'
      addLogEntry({ type: 'error', content: errMsg, iterationId })
      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId ? { ...n, status: 'error', error: errMsg } : n
      ))
      setError(errMsg)
      setPhase('idle')
      setIsLoading(false)
    }
  }, [backtestParams, addLogEntry, updateLogEntry, startProgressTimers, clearProgressTimers, applyRealTimings])

  // ==========================================================================
  // editAndRerun — execute with edited script code (skip generation)
  // ==========================================================================

  const editAndRerun = useCallback(async (originalIterationId: string, editedCode: string) => {
    // Find the original iteration to get context
    const original = iterationHistory.find(n => n.id === originalIterationId)
    if (!original) return

    setPhase('executing')
    setIsLoading(true)
    setError(null)

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

    // Create new iteration
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
    }
    setIterationHistory(prev => [...prev, newIteration])

    // Step entries
    const validateStepId = addLogEntry({
      type: 'ai-step', content: 'Validating code...', status: 'active', startedAt: Date.now(), iterationId,
    })
    const fetchStepId = addLogEntry({
      type: 'ai-step', content: 'Fetching market data...', status: 'pending', iterationId,
    })
    const simStepId = addLogEntry({
      type: 'ai-step', content: 'Running simulation...', status: 'pending', iterationId,
    })
    const calcStepId = addLogEntry({
      type: 'ai-step', content: 'Calculating metrics...', status: 'pending', iterationId,
    })
    const metricSubStepIds = METRIC_SUBSTEPS.map(label =>
      addLogEntry({
        type: 'ai-step', content: label, status: 'pending', substep: true, iterationId,
      })
    )

    const stepIds = { validate: validateStepId, fetch: fetchStepId, sim: simStepId, calc: calcStepId, metrics: metricSubStepIds }
    const executionStartTime = Date.now()

    // Animate estimated progress while API call is in-flight
    startProgressTimers(stepIds)

    try {
      const response = await fetch(`${API_BASE_URL}/api/execute-backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          script_id: original.scriptId,
          script_code: editedCode,
          symbol: backtestParams.symbol,
          timeframe: backtestParams.timeframe,
          start_date: backtestParams.start_date,
          end_date: backtestParams.end_date,
          initial_capital: backtestParams.initial_capital,
        }),
      })

      const data = await response.json()

      // Stop estimated timers — real timings will overwrite
      clearProgressTimers()

      if (!data.success) {
        const errMsg = data.errors?.join(', ') || 'Backtest execution failed'
        const errNow = Date.now()
        updateLogEntry(validateStepId, { status: 'done', completedAt: errNow })
        updateLogEntry(fetchStepId, { status: 'done', completedAt: errNow })
        updateLogEntry(simStepId, { status: 'done', completedAt: errNow })
        updateLogEntry(calcStepId, { status: 'error', completedAt: errNow })
        metricSubStepIds.forEach(id => updateLogEntry(id, { status: 'error', completedAt: errNow }))
        addLogEntry({ type: 'error', content: errMsg, iterationId })
        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId ? { ...n, status: 'error', error: errMsg } : n
        ))
        setError(errMsg)
        setPhase('idle')
        setIsLoading(false)
        return
      }

      // Overwrite with real backend timings
      applyRealTimings(data.timings, executionStartTime, stepIds)

      const backtestResult: BacktestResult = data.result
      const resultRating: StrategyRating | null = data.rating || null

      const returnPct = (backtestResult.total_return * 100).toFixed(2)
      const returnSign = backtestResult.total_return >= 0 ? '+' : ''
      addLogEntry({
        type: 'complete',
        content: `${returnSign}${returnPct}% return, ${backtestResult.num_trades} trades, ${(backtestResult.win_rate * 100).toFixed(0)}% win rate, ${backtestResult.sharpe_ratio.toFixed(2)} sharpe`,
        iterationId,
      })

      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId
          ? {
              ...n,
              result: backtestResult,
              rating: resultRating,
              totalReturn: backtestResult.total_return,
              winRate: backtestResult.win_rate,
              numTrades: backtestResult.num_trades,
              sharpe: backtestResult.sharpe_ratio,
              status: 'complete',
            }
          : n
      ))

      setPhase('results')
      setIsLoading(false)
    } catch (err) {
      clearProgressTimers()
      const errMsg = err instanceof Error ? err.message : 'Failed to execute backtest'
      addLogEntry({ type: 'error', content: errMsg, iterationId })
      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId ? { ...n, status: 'error', error: errMsg } : n
      ))
      setError(errMsg)
      setPhase('idle')
      setIsLoading(false)
    }
  }, [iterationHistory, backtestParams, addLogEntry, updateLogEntry, startProgressTimers, clearProgressTimers, applyRealTimings])

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
    deleteIteration,
    selectIteration,
    resetToIdle,
    archivedSessions,
    newSession,
    switchSession,
    deleteArchivedSession,
  }
}
