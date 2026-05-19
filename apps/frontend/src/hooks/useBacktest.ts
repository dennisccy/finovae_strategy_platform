import { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import {
  loadSession as apiLoadSession,
  saveSessionMeta,
  appendActivityEntries as apiAppendActivity,
  rewriteActivityLog as apiRewriteActivity,
  upsertIteration,
  deleteIterationFromStore,
  fetchIterationDetail,
  beaconSaveSession,
} from '../lib/sessionApi'
import { FALLBACK_MODEL } from '../lib/modelsApi'

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

function createSemaphore(n: number) {
  let count = 0
  const queue: Array<() => void> = []
  return {
    acquire: () => new Promise<void>(resolve => {
      if (count < n) { count++; resolve() }
      else queue.push(() => { count++; resolve() })
    }),
    release: () => {
      count--
      queue.shift()?.()
    },
  }
}

// =============================================================================
// Session Persistence Types
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
}

function migrateSession(data: SessionData): SessionData {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const params = data.backtestParams as any
  // Migrate timeframes: string[] → timeframe: string (multi-timeframe removed)
  if ('timeframes' in params && !('timeframe' in params)) {
    params.timeframe = (Array.isArray(params.timeframes) ? params.timeframes[0] : params.timeframes) ?? '4h'
    delete params.timeframes
  }
  if (!params.timeframe || typeof params.timeframe !== 'string') {
    params.timeframe = '4h'
  }
  // Migrate old sessions without exchange field
  if (!('exchange' in params)) {
    params.exchange = 'binance'
  }
  // Migrate old sessions without allow_short / leverage fields (v0.7)
  if (!('allow_short' in params)) {
    params.allow_short = false
  }
  if (!('leverage' in params)) {
    params.leverage = 1
  }
  // Strip removed multi-timeframe fields from iteration nodes
  data.iterationHistory = data.iterationHistory.map(n => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const node = n as any
    delete node.timeframeResults
    delete node.activeTimeframe
    if (!('maxDrawdown' in node)) {
      node.maxDrawdown = node.result?.max_drawdown ?? 0
    }
    return n
  })
  return data
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
  direction?: string   // "long" | "short" — v0.7 additive
  leverage?: number    // leverage multiplier — v0.7 additive
  margin?: number      // cash collateral posted — v0.8 additive
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
  margin_called?: boolean        // v0.8 additive
  unleveraged_return?: number    // v0.8 additive; null/undefined when leverage == 1
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
  annual_long_returns: Record<number, number>
  annual_short_returns: Record<number, number>
}

// =============================================================================
// Walk-Forward Validation Types (v0.10 additive)
// =============================================================================

export interface WalkForwardWindow {
  window_index: number
  is_start: string
  is_end: string
  oos_start: string
  oos_end: string
  is_total_return: number
  oos_total_return: number
  is_sharpe: number
  oos_sharpe: number
  is_num_trades: number
  oos_num_trades: number
  oos_equity_curve: EquityPoint[]
}

export interface WalkForwardResult {
  windows: WalkForwardWindow[]
  num_windows: number
  is_months: number
  oos_months: number
  combined_oos_return: number
  combined_oos_sharpe: number
  combined_oos_win_rate: number
  combined_oos_max_drawdown: number
  wfe: number
  combined_oos_equity: EquityPoint[]
  errors: string[]
}

export interface WalkForwardConfig {
  isMonths: number
  oosMonths: number
  maxWindows?: number
}

export interface InsightsSuggestion {
  title: string
  description: string
  prompt: string
  disabled?: boolean   // true = tried by auto-run and discarded; skip on next run
  batchIndex?: number  // which generation batch, 0-based; undefined treated as 0
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
  timeframe: string
  start_date: string
  end_date: string
  initial_capital: number
  exchange: string
  allow_short?: boolean          // v0.7 additive
  leverage?: number              // v0.7 additive
  max_order_size_pct?: number    // v0.9 additive — undefined = disabled
  max_daily_loss_pct?: number    // v0.9 additive — undefined = disabled
}

export const EXCHANGE_CONFIGS: Record<string, { label: string; commission: number }> = {
  binance: { label: 'Binance', commission: 0.00075 },
  bybit: { label: 'Bybit', commission: 0.001 },
  okx: { label: 'OKX', commission: 0.001 },
  kraken: { label: 'Kraken', commission: 0.0026 },
  coinbase: { label: 'Coinbase', commission: 0.006 },
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
  modelUsed?: string
  params?: BacktestParams
  parentId?: string | null  // null/undefined = root; string = child of that iteration ID
  walkForwardResult?: WalkForwardResult | null   // v0.10 additive
  walkForwardStatus?: 'idle' | 'running' | 'complete' | 'error'  // v0.10 additive
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
  isFetchingSession: boolean
  iterationCount: number
  bestReturn: number | null
  hasError: boolean
}

// Headless auto-session status block. Mirrors the small `autoRun` object the
// backend persists into session.json (durable file store) and returns from
// GET /api/sessions/{id}. Present only for backend-owned (headless) sessions;
// null for manual sessions.
export type AutoRunPhase = 'queued' | 'running' | 'complete' | 'stopped'

export interface AutoRunStatus {
  status: AutoRunPhase
  stopReason: 'criteria-met' | 'budget-exhausted' | null
  currentIteration: number
  maxIterations: number
  bestIterationId: string | null
  startedAt?: string
  updatedAt?: string
}

// =============================================================================
// Hook
// =============================================================================

const DEFAULT_PARAMS: BacktestParams = {
  symbol: 'BNB/USDT',
  timeframe: '4h',
  start_date: '2020-01-01',
  end_date: '2024-01-01',
  initial_capital: 1500,
  exchange: 'binance',
}

export function useBacktest(sessionId: string) {
  const [isHydrated, setIsHydrated] = useState(false)
  const [phase, setPhase] = useState<Phase>('idle')
  const [isLoading, setIsLoading] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Lazy per-iteration detail fetch (the session list/open path is now
  // lightweight — heavy result/rating/scriptCode is fetched on selection).
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  // id of an in-flight detail fetch (dedupe concurrent triggers for the same
  // node). Detail-present is read off the node's own `result`, not a
  // hook-lifetime id set — a long-lived "already loaded" ref goes stale when
  // the history is re-hydrated/polled back to lightweight (result: null) and
  // would then permanently block re-fetch of the selected run (J-02).
  const loadingDetailIdRef = useRef<string | null>(null)

  // Auto-run state
  const [isAutoRunning, setIsAutoRunning] = useState(false)
  const [autoRunProgress, setAutoRunProgress] = useState<{ current: number; max: number } | null>(null)
  const autoRunStopRef = useRef(false)
  const autoRunIterationIdsRef = useRef<Set<string>>(new Set())

  // Headless (server-driven) auto-session status. Set from the durable
  // session.json `autoRun` block on hydration and refreshed by lightweight
  // polling while the run is active. When non-null the session is
  // backend-owned: the backend is the single writer of its artifacts, so the
  // frontend save effects are suppressed (read-only live monitoring view).
  const [autoRun, setAutoRun] = useState<AutoRunStatus | null>(null)
  const backendOwnedRef = useRef(false)

  // Worker count (fetched from /api/config; controls auto-run concurrency)
  const [workerCount, setWorkerCount] = useState(1)
  const workerCountRef = useRef(1)
  useEffect(() => { workerCountRef.current = workerCount }, [workerCount])

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/config`)
      .then(r => r.json())
      .then(data => {
        const n = typeof data.workers === 'number' && data.workers > 0 ? data.workers : 1
        setWorkerCount(n)
      })
      .catch(() => { /* default 1 */ })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Liquidity cache: computed once per symbol/timeframe/period, reused across iterations
  const cachedLiquidityRef = useRef<{
    liquidity: CategoryRating
    capacity_levels: CapacityLevel[]
  } | null>(null)

  const [activityLog, setActivityLog] = useState<ActivityEntry[]>([])
  const [selectedIterationId, setSelectedIterationId] = useState<string | null>(null)
  const [iterationHistory, setIterationHistory] = useState<IterationNode[]>([])

  const iterationHistoryRef = useRef<IterationNode[]>([])
  useEffect(() => { iterationHistoryRef.current = iterationHistory }, [iterationHistory])

  const [backtestParams, setBacktestParams] = useState<BacktestParams>(DEFAULT_PARAMS)

  // Refs to keep latest values for the beacon handler
  const backtestParamsRef = useRef<BacktestParams>(DEFAULT_PARAMS)
  useEffect(() => { backtestParamsRef.current = backtestParams }, [backtestParams])
  const selectedIterationIdRef = useRef<string | null>(null)
  useEffect(() => { selectedIterationIdRef.current = selectedIterationId }, [selectedIterationId])

  // Refs for save tracking — declared before hydration effect so they can be
  // pre-populated during hydration to prevent re-saving restored data.
  const savedIterationVersionRef = useRef<Map<string, string>>(new Map())
  const savedActivityCountRef = useRef(0)
  const activityRewriteTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const metaSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Async hydration — load session from backend on mount
  useEffect(() => {
    let cancelled = false
    apiLoadSession(sessionId).then(raw => {
      if (cancelled) return
      if (raw) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const data = raw as any
        // A non-null `autoRun` block ⇒ this session was created by the
        // headless controller and the backend owns its artifacts.
        const auto = (data.autoRun ?? null) as AutoRunStatus | null
        backendOwnedRef.current = !!auto
        setAutoRun(auto)
        const migrated = migrateSession({
          iterationHistory: Array.isArray(data.iterationHistory) ? data.iterationHistory : [],
          activityLog: Array.isArray(data.activityLog) ? data.activityLog : [],
          backtestParams: data.backtestParams ?? DEFAULT_PARAMS,
          selectedIterationId: data.selectedIterationId ?? null,
        })

        // The list/open path is lightweight: it omits the heavy/bulk fields
        // (prompt, scriptCode, result, rating, insights). Normalize each node
        // back to the IterationNode contract's nullable defaults so list/tree
        // rendering never reads an undefined heavy field (e.g. prompt.length);
        // the real values are lazy-merged on selection.
        const normalizeLightweight = (n: IterationNode): IterationNode => ({
          ...n,
          prompt: n.prompt ?? '',
          scriptCode: n.scriptCode ?? '',
          scriptId: n.scriptId ?? '',
          result: n.result ?? null,
          rating: n.rating ?? null,
          insights: n.insights ?? null,
        })

        // Fix up in-progress statuses that survived a page reload
        const restoredHistory = migrated.iterationHistory.flatMap((n: IterationNode) => {
          if (n.status === 'generating' || n.status === 'executing') {
            if (n.result) return [normalizeLightweight({ ...n, status: 'complete' as const })]
            return []
          }
          if (n.status !== 'complete') return []  // drop error/cancelled/unknown on reload
          return [normalizeLightweight(n)]
        })

        const restoredIds = new Set(restoredHistory.map((n: IterationNode) => n.id))
        const restoredActivity = migrated.activityLog
          .filter((e: ActivityEntry) => !e.iterationId || restoredIds.has(e.iterationId))
          .map((e: ActivityEntry) =>
            (e.status === 'active' || e.status === 'pending')
              ? { ...e, status: 'done' as const, completedAt: e.completedAt ?? Date.now() }
              : e
          )

        // Determine selected iteration (validate it still exists after filter)
        const savedId = migrated.selectedIterationId
        let resolvedId: string | null = null
        if (savedId) {
          const found = restoredHistory.find((n: IterationNode) => n.id === savedId)
          if (found) {
            resolvedId = savedId
          } else {
            const last = [...restoredHistory].reverse().find(
              (n: IterationNode) => n.status === 'complete' || !!n.result
            )
            resolvedId = last?.id ?? null
          }
        }

        // Pre-populate refs so save effects don't re-save already-stored data
        savedActivityCountRef.current = restoredActivity.length
        restoredHistory.forEach((n: IterationNode) => {
          if (n.status === 'complete' || n.status === 'error') {
            const vk = `${n.status}:${n.insights?.suggestions?.length ?? 0}`
            savedIterationVersionRef.current.set(n.id, vk)
          }
        })

        const latestComplete = restoredHistory
          .filter((n: IterationNode) => n.status === 'complete' && n.params)
          .sort((a: IterationNode, b: IterationNode) =>
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
          )[0] ?? null
        setIterationHistory(restoredHistory)
        setActivityLog(restoredActivity)
        setBacktestParams(latestComplete?.params ?? migrated.backtestParams)
        setSelectedIterationId(resolvedId)
        if (restoredHistory.some((n: IterationNode) =>
          n.status === 'complete' || ((n.status === 'generating' || n.status === 'executing') && !!n.result)
        )) {
          setPhase('results')
        }
      }
      setIsHydrated(true)
    }).catch(() => {
      if (!cancelled) setIsHydrated(true)
    })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  // ==========================================================================
  // Granular save effects (replaces monolithic localStorage save)
  // ==========================================================================

  // Save completed/errored iterations when they change
  useEffect(() => {
    // Backend-owned (headless) sessions: the server is the single writer of
    // its iteration/activity/meta artifacts. Persisting the lightweight
    // polled view back would overwrite the server's full result.json /
    // rating.json with nulls — suppress all client writes for them.
    if (!isHydrated || backendOwnedRef.current) return
    let savedAny = false
    iterationHistory.forEach((node, idx) => {
      if (node.status !== 'complete' && node.status !== 'error') return
      const versionKey = `${node.status}:${node.insights?.suggestions?.length ?? 0}`
      if (savedIterationVersionRef.current.get(node.id) !== versionKey) {
        savedIterationVersionRef.current.set(node.id, versionKey)
        upsertIteration(sessionId, idx + 1, node)
        savedAny = true
      }
    })
    // When iterations are saved, immediately flush meta to ensure session.json exists
    if (savedAny) {
      if (metaSaveTimerRef.current) clearTimeout(metaSaveTimerRef.current)
      metaSaveTimerRef.current = null
      saveSessionMeta(sessionId, {
        backtestParams: backtestParamsRef.current,
        selectedIterationId: selectedIterationIdRef.current,
      })
    }
  }, [isHydrated, sessionId, iterationHistory])

  // Activity log: append new entries immediately; debounced rewrite for updates
  useEffect(() => {
    if (!isHydrated || backendOwnedRef.current) return
    const prev = savedActivityCountRef.current
    const curr = activityLog.length

    if (curr > prev) {
      const newEntries = activityLog.slice(prev)
      savedActivityCountRef.current = curr
      // Clear pending rewrite to prevent stale snapshot overwriting new entries
      if (activityRewriteTimerRef.current) {
        clearTimeout(activityRewriteTimerRef.current)
        activityRewriteTimerRef.current = null
      }
      apiAppendActivity(sessionId, newEntries)
    } else if (curr !== prev || (curr === prev && curr > 0)) {
      // Entries updated or deleted — debounced rewrite
      if (activityRewriteTimerRef.current) clearTimeout(activityRewriteTimerRef.current)
      const snapshot = [...activityLog]
      savedActivityCountRef.current = curr
      activityRewriteTimerRef.current = setTimeout(() => {
        apiRewriteActivity(sessionId, snapshot)
      }, 1000)
    }
  }, [isHydrated, sessionId, activityLog])

  // Meta save: debounced 2s on params / selectedIteration change
  useEffect(() => {
    if (!isHydrated || backendOwnedRef.current) return
    if (metaSaveTimerRef.current) clearTimeout(metaSaveTimerRef.current)
    const params = backtestParams
    const selId = selectedIterationId
    metaSaveTimerRef.current = setTimeout(() => {
      saveSessionMeta(sessionId, { backtestParams: params, selectedIterationId: selId })
    }, 2000)
    return () => { if (metaSaveTimerRef.current) clearTimeout(metaSaveTimerRef.current) }
  }, [isHydrated, sessionId, backtestParams, selectedIterationId])

  // Beacon save on page unload (fire-and-forget, survives page close)
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (backendOwnedRef.current) return
      beaconSaveSession(sessionId, {
        backtestParams: backtestParamsRef.current,
        selectedIterationId: selectedIterationIdRef.current,
      })
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [sessionId])

  // Live tracking for headless auto-sessions (J-08): while the server-driven
  // run is active, poll the lightweight session/open path and merge changes
  // in — no manual page reload. Polling stops the moment the run reaches a
  // terminal state. The merge MUST preserve any already-lazy-loaded heavy
  // detail (result/rating/insights/scriptCode/WF): the polled list path is
  // lightweight (those fields are null) and must never downgrade a node the
  // user has open.
  useEffect(() => {
    if (!isHydrated) return
    const phase = autoRun?.status
    if (phase !== 'running' && phase !== 'queued') return

    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null

    const tick = async () => {
      const raw = await apiLoadSession(sessionId)
      if (cancelled || !raw) return
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data = raw as any
      const nextAuto = (data.autoRun ?? null) as AutoRunStatus | null
      if (nextAuto) {
        backendOwnedRef.current = true
        setAutoRun(nextAuto)
      }

      const incoming: IterationNode[] = (
        Array.isArray(data.iterationHistory) ? data.iterationHistory : []
      ).filter((n: IterationNode) => n.status === 'complete')

      setIterationHistory(prev => {
        const prevById = new Map(prev.map(n => [n.id, n]))
        const merged: IterationNode[] = prev.map(n => {
          const inc = incoming.find(i => i.id === n.id)
          if (!inc) return n
          // Refresh lightweight meta from the poll but PRESERVE locally
          // lazy-loaded heavy fields (mirror loadIterationDetail precedence).
          return {
            ...inc,
            prompt: n.prompt || inc.prompt || '',
            scriptCode: n.scriptCode || inc.scriptCode || '',
            scriptId: n.scriptId || inc.scriptId || '',
            result: n.result ?? null,
            rating: n.rating ?? null,
            insights: n.insights ?? inc.insights ?? null,
            walkForwardResult: n.walkForwardResult ?? null,
            walkForwardStatus: n.walkForwardStatus ?? inc.walkForwardStatus,
          }
        })
        for (const inc of incoming) {
          if (!prevById.has(inc.id)) {
            merged.push({
              ...inc,
              prompt: inc.prompt ?? '',
              scriptCode: inc.scriptCode ?? '',
              scriptId: inc.scriptId ?? '',
              result: inc.result ?? null,
              rating: inc.rating ?? null,
              insights: inc.insights ?? null,
            })
          }
        }
        // Keep the save-version map aligned (defence-in-depth: save effects
        // are already suppressed for backend-owned sessions).
        merged.forEach(m => {
          if (m.status === 'complete' || m.status === 'error') {
            savedIterationVersionRef.current.set(
              m.id, `${m.status}:${m.insights?.suggestions?.length ?? 0}`
            )
          }
        })
        iterationHistoryRef.current = merged
        return merged
      })

      if (Array.isArray(data.activityLog)) {
        savedActivityCountRef.current = data.activityLog.length
        setActivityLog(data.activityLog as ActivityEntry[])
      }
      if (incoming.length > 0) setPhase('results')

      if (!cancelled) timer = setTimeout(tick, 2500)
    }

    timer = setTimeout(tick, 2500)
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [isHydrated, sessionId, autoRun?.status])

  // Derived live session status for multi-session UI
  const sessionStatus: LiveSessionStatus = useMemo(() => {
    // Lightweight nodes carry totalReturn even before heavy detail loads, so
    // key off it (not n.result) — otherwise a headless session shows no best
    // return in the list until a run is opened.
    const completedNodes = iterationHistory.filter(n => n.status === 'complete')
    const bestReturn = completedNodes.length > 0
      ? Math.max(...completedNodes.map(n => n.totalReturn))
      : null
    const firstComplete = iterationHistory.find(n => n.status === 'complete')
    const name = firstComplete?.strategyName || `Session`
    // A live headless run also drives the session-list activity dot
    // (running → terminal) without a manual reload.
    const headlessActive = autoRun?.status === 'running' || autoRun?.status === 'queued'
    return {
      id: sessionId,
      name,
      isLoading,
      isAutoRunning: isAutoRunning || headlessActive,
      isFetchingSession: !isHydrated,
      iterationCount: iterationHistory.length,
      bestReturn,
      hasError: iterationHistory.some(n => n.status === 'error'),
    }
  }, [sessionId, isLoading, isAutoRunning, isHydrated, iterationHistory, autoRun?.status])

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

  /** Cancel the currently running operation. */
  const cancelOperation = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null

    setPhase('idle')
    setIsLoading(false)

    setIterationHistory(prev => prev.map(n => {
      if (n.status === 'generating' || n.status === 'executing') {
        return { ...n, status: 'error' as const, error: 'Cancelled by user' }
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
  }, [])

  /** Apply real backend timings to step entries. */
  const applyRealTimings = useCallback((
    timings: { validate_ms: number; fetch_ms: number; simulate_ms: number; calculate_ms: number; walk_forward_ms?: number | null; total_ms?: number; calculate_steps?: Record<string, number> | null } | undefined,
    base: number,
    stepIds: { validate: string; fetch: string; sim: string; calc: string; metrics: string[]; wf?: string | null },
    resultArrivedAt?: number,
  ) => {
    if (timings) {
      // Anchor to server execution end time (result arrived - total server time) for
      // accurate alignment regardless of network latency or semaphore wait.
      const effectiveBase = (resultArrivedAt && timings.total_ms)
        ? resultArrivedAt - timings.total_ms
        : base
      const validateEnd = effectiveBase + timings.validate_ms
      const fetchEnd = validateEnd + timings.fetch_ms
      const simEnd = fetchEnd + timings.simulate_ms
      const calcEnd = simEnd + timings.calculate_ms

      updateLogEntry(stepIds.validate, { status: 'done', startedAt: effectiveBase, completedAt: validateEnd })
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

      if (stepIds.wf && timings.walk_forward_ms != null) {
        const wfStart = calcEnd
        const wfEnd = wfStart + timings.walk_forward_ms
        updateLogEntry(stepIds.wf, { status: 'done', startedAt: wfStart, completedAt: wfEnd })
      }
    } else {
      const now = Date.now()
      updateLogEntry(stepIds.validate, { status: 'done', completedAt: now })
      updateLogEntry(stepIds.fetch, { status: 'done', completedAt: now })
      updateLogEntry(stepIds.sim, { status: 'done', completedAt: now })
      updateLogEntry(stepIds.calc, { status: 'done', completedAt: now })
      stepIds.metrics.forEach(id => updateLogEntry(id, { status: 'done', completedAt: now }))
      if (stepIds.wf) updateLogEntry(stepIds.wf, { status: 'done', completedAt: now })
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
    directionId?: string,
    directionIndex?: number,
    directionPrompt?: string,
    wfvConfig?: WalkForwardConfig | null,
  ): Promise<{ result: BacktestResult; rating: StrategyRating | null; walkForwardResult: WalkForwardResult | null } | null> => {
    const validateStepId = addLogEntry({
      type: 'ai-step', content: `[${timeframe}] Validating code...`, status: 'active', startedAt: Date.now(), iterationId,
    })
    const validateSubStepIds = [
      addLogEntry({ type: 'ai-step', content: `[${timeframe}] Pattern check`, status: 'pending', substep: true, iterationId }),
      addLogEntry({ type: 'ai-step', content: `[${timeframe}] Compiling strategy`, status: 'pending', substep: true, iterationId }),
      addLogEntry({ type: 'ai-step', content: `[${timeframe}] Instantiating class`, status: 'pending', substep: true, iterationId }),
      addLogEntry({ type: 'ai-step', content: `[${timeframe}] Setup & signal wire-up`, status: 'pending', substep: true, iterationId }),
    ]
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

    const wfStepId = wfvConfig ? addLogEntry({
      type: 'ai-step', content: `[${timeframe}] Walk-Forward Validation...`, status: 'pending', iterationId,
    }) : null

    const stepIds = { validate: validateStepId, fetch: fetchStepId, sim: simStepId, calc: calcStepId, metrics: metricSubStepIds, wf: wfStepId }
    const executionStartTime = Date.now()

    const donePhases = new Set<string>()
    const startedPhases = new Set<string>()
    const startedSubstepIds = new Set<number>()

    const phaseOrder = ['validate', 'fetch', 'simulate', 'calculate', 'walk_forward'] as const
    const phaseToStepId: Record<string, string> = {
      validate: validateStepId,
      fetch: fetchStepId,
      simulate: simStepId,
      calculate: calcStepId,
      ...(wfStepId ? { walk_forward: wfStepId } : {}),
    }

    const applyPolledStatus = (status: {
      phase: string
      validate_step?: string | null
      calculate_step?: string | null
      calculate_step_index?: number
      sim_bar?: number
      sim_total_bars?: number
    }) => {
      const currentPhaseIdx = phaseOrder.indexOf(status.phase as typeof phaseOrder[number])

      for (let p = 0; p < currentPhaseIdx; p++) {
        const phaseName = phaseOrder[p]
        if (!donePhases.has(phaseName)) {
          donePhases.add(phaseName)
          const now = Date.now()
          updateLogEntry(phaseToStepId[phaseName], { status: 'done', completedAt: now })
          // Mark all validate sub-steps done when moving past validate phase
          if (phaseName === 'validate') {
            validateSubStepIds.forEach(id => updateLogEntry(id, { status: 'done', completedAt: now }))
          }
        }
      }

      if (currentPhaseIdx >= 0) {
        const currentPhase = phaseOrder[currentPhaseIdx]
        if (!donePhases.has(currentPhase) && !startedPhases.has(currentPhase)) {
          startedPhases.add(currentPhase)
          updateLogEntry(phaseToStepId[currentPhase], { status: 'active', startedAt: Date.now() })
        }
      }

      // Validate sub-steps
      if (status.phase === 'validate' && status.validate_step) {
        const stepMap: Record<string, number> = {
          pattern_check: 0,
          compile: 1,
          instantiate: 2,
          setup_signal: 3,
        }
        const activeIdx = stepMap[status.validate_step] ?? -1
        validateSubStepIds.forEach((id, i) => {
          if (i < activeIdx) {
            updateLogEntry(id, { status: 'done', completedAt: Date.now() })
          } else if (i === activeIdx) {
            updateLogEntry(id, { status: 'active', startedAt: Date.now() })
          }
        })
      }

      if (status.phase === 'simulate' && (status.sim_total_bars ?? 0) > 0) {
        const pct = Math.round(((status.sim_bar ?? 0) / (status.sim_total_bars ?? 1)) * 100)
        updateLogEntry(simStepId, {
          status: 'active',
          content: `[${timeframe}] Running simulation... ${pct}%`,
        })
      }

      if (status.phase === 'calculate') {
        const doneUpTo = status.calculate_step_index ?? 0
        for (let s = 0; s < metricSubStepIds.length; s++) {
          if (s < doneUpTo) {
            updateLogEntry(metricSubStepIds[s], { status: 'done', completedAt: Date.now() })
          } else if (s === doneUpTo && !startedSubstepIds.has(s)) {
            startedSubstepIds.add(s)
            updateLogEntry(metricSubStepIds[s], { status: 'active', startedAt: Date.now() })
          }
        }
      }

      if (status.phase === 'walk_forward' && wfStepId) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const wfWindow = (status as any).wf_window ?? 0
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const wfTotal = (status as any).wf_total ?? 0
        if (wfTotal > 0) {
          updateLogEntry(wfStepId, {
            status: 'active',
            content: `[${timeframe}] Walk-Forward window ${wfWindow} / ${wfTotal}`,
          })
        } else {
          updateLogEntry(wfStepId, { status: 'active' })
        }
      }
    }

    try {
      const body = JSON.stringify({
        script_id: scriptId,
        script_code: scriptCode,
        symbol: symbolOverride ?? backtestParams.symbol,
        timeframe,
        start_date: backtestParams.start_date,
        end_date: backtestParams.end_date,
        initial_capital: backtestParams.initial_capital,
        commission: EXCHANGE_CONFIGS[backtestParams.exchange]?.commission ?? 0.00075,
        allow_short: backtestParams.allow_short ?? false,
        leverage: backtestParams.leverage ?? 1,
        ...(backtestParams.max_order_size_pct !== undefined
          ? { max_order_size_pct: backtestParams.max_order_size_pct } : {}),
        ...(backtestParams.max_daily_loss_pct !== undefined
          ? { max_daily_loss_pct: backtestParams.max_daily_loss_pct } : {}),
        ...(directionId ? {
          exchange: backtestParams.exchange,
          direction_id: directionId,
          direction_index: directionIndex ?? 0,
          direction_prompt: directionPrompt ?? '',
        } : {}),
        strategy_name: directionPrompt ?? undefined,
        ...(wfvConfig ? {
          wfv_enabled: true,
          wfv_is_months: wfvConfig.isMonths,
          wfv_oos_months: wfvConfig.oosMonths,
          ...(wfvConfig.maxWindows !== undefined ? { wfv_max_windows: wfvConfig.maxWindows } : {}),
        } : {}),
      })

      // Retry on transient "Failed to fetch" network errors (e.g. server busy during concurrent load)
      let execResponse: Response | null = null
      const MAX_RETRIES = 3
      for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
        if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
        if (attempt > 0) {
          await new Promise(r => setTimeout(r, 500 * Math.pow(2, attempt - 1)))
          addLogEntry({ type: 'ai-step', content: `[${timeframe}] Retrying... (attempt ${attempt + 1})`, status: 'active', iterationId, substep: true })
        }
        try {
          execResponse = await fetch(`${API_BASE_URL}/api/execute-backtest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body,
            signal,
          })
          break  // success — exit retry loop
        } catch (fetchErr) {
          if (fetchErr instanceof DOMException && fetchErr.name === 'AbortError') throw fetchErr
          if (attempt === MAX_RETRIES - 1) throw fetchErr  // propagate on last attempt
          console.warn(`[${timeframe}] Fetch attempt ${attempt + 1} failed, retrying...`, fetchErr)
        }
      }

      if (!execResponse!.ok) {
        throw new Error(`HTTP ${execResponse!.status}`)
      }

      // Read SSE stream — status events update the UI in real-time; final event carries result
      const reader = execResponse!.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let execData: any = null
      let resultArrivedAt = 0

      outer: while (!execData) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''
        for (const part of parts) {
          for (const line of part.split('\n')) {
            if (!line.startsWith('data: ')) continue
            const event = JSON.parse(line.slice(6))
            if (event.type === 'status') {
              applyPolledStatus({
                phase: event.phase,
                validate_step: event.validate_step,
                calculate_step: event.calculate_step,
                calculate_step_index: event.calculate_step_index,
                sim_bar: event.sim_bar,
                sim_total_bars: event.sim_total_bars,
              })
            } else if (event.type === 'result' || event.type === 'error') {
              resultArrivedAt = Date.now()
              execData = event
              break outer
            }
          }
        }
      }
      reader.releaseLock()

      if (!execData || !execData.success) {
        const errNow = Date.now()
        validateSubStepIds.forEach(id => updateLogEntry(id, { status: 'done', completedAt: errNow }))
        updateLogEntry(validateStepId, { status: 'done', completedAt: errNow })
        updateLogEntry(fetchStepId, { status: 'done', completedAt: errNow })
        updateLogEntry(simStepId, { status: 'done', completedAt: errNow })
        updateLogEntry(calcStepId, { status: 'error', completedAt: errNow })
        metricSubStepIds.forEach(id => updateLogEntry(id, { status: 'error', completedAt: errNow }))
        const backendErrors: string[] = execData?.errors || []
        const errMsg = backendErrors.length > 0
          ? backendErrors.join('; ')
          : `Backtest failed for ${timeframe}`
        addLogEntry({ type: 'error', content: `[${timeframe}] ${errMsg}`, iterationId })
        return null
      }

      applyRealTimings(execData.timings, executionStartTime, stepIds, resultArrivedAt)
      return {
        result: execData.result as BacktestResult,
        rating: (execData.rating as StrategyRating) || null,
        walkForwardResult: execData.walk_forward_result
          ? _trimWalkForwardForStorage(execData.walk_forward_result as WalkForwardResult)
          : null,
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        return null
      }

      const errNow = Date.now()
      updateLogEntry(validateStepId, { status: 'done', completedAt: errNow })
      updateLogEntry(fetchStepId, { status: 'done', completedAt: errNow })
      updateLogEntry(simStepId, { status: 'done', completedAt: errNow })
      updateLogEntry(calcStepId, { status: 'error', completedAt: errNow })
      metricSubStepIds.forEach(id => updateLogEntry(id, { status: 'error', completedAt: errNow }))

      const errMsg = err instanceof Error ? err.message : 'Unknown network error'
      addLogEntry({ type: 'error', content: `[${timeframe}] Fetch error: ${errMsg}`, iterationId })
      return null
    }
  }, [backtestParams, addLogEntry, updateLogEntry, applyRealTimings])

  // ==========================================================================
  // validateSymbolExists
  // ==========================================================================

  const validationCacheRef = useRef<Record<string, Promise<string | null> | undefined>>({})

  const validateSymbolExists = useCallback(async (symbol: string): Promise<string | null> => {
    if (!/^[A-Z]+\/USDT$/.test(symbol)) {
      return `Symbol must be in BASE/USDT format (e.g. PEPE/USDT)`
    }

    const cachedPromise = validationCacheRef.current[symbol]
    if (cachedPromise) {
      return cachedPromise
    }

    const validatePromise = (async () => {
      try {
        const baseUrl = import.meta.env.VITE_API_URL ?? ''
        const resp = await fetch(`${baseUrl}/api/validate-symbol?symbol=${encodeURIComponent(symbol)}`)
        const data = await resp.json()
        return data.valid ? null : (data.error ?? `${symbol} not found on Binance`)
      } catch {
        return null // Network error: let backtest proceed, backend will catch
      } finally {
        setTimeout(() => {
          delete validationCacheRef.current[symbol]
        }, 1000)
      }
    })()

    validationCacheRef.current[symbol] = validatePromise
    return validatePromise
  }, [])

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
    sharedSignal?: AbortSignal,
    directionId?: string,
    directionIndex?: number,
    directionPrompt?: string,
    parentId?: string | null,
    overrideParams?: Partial<typeof backtestParams>,
    wfvConfig?: WalkForwardConfig | null,
  ) => {
    // Deduplicate: if already loading, abort the previous request first (unless explicitly running concurrently)
    if (!sharedSignal && abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }

    const symbolToCheck = overrideSymbol ?? backtestParams.symbol
    const symbolErr = await validateSymbolExists(symbolToCheck)
    if (symbolErr) {
      const iterationId = crypto.randomUUID()
      addLogEntry({ type: 'error', content: `Invalid symbol: ${symbolErr}`, iterationId })
      setIsLoading(false)
      return null
    }

    setPhase('generating')
    setIsLoading(true)
    setError(null)

    let signal = sharedSignal
    if (!signal) {
      const abortController = new AbortController()
      abortControllerRef.current = abortController
      signal = abortController.signal
    }

    const iterationId = crypto.randomUUID()
    addLogEntry({
      type: 'user-prompt',
      content: prompt,
      iterationId,
    })

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
      params: { ...backtestParams, ...overrideParams },
      timestamp: new Date().toISOString(),
      status: 'generating',
      parentId: parentId ?? null,
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
        timeframe: overrideTimeframes?.[0] ?? backtestParams.timeframe,
        start_date: backtestParams.start_date,
        end_date: backtestParams.end_date,
        allow_short: backtestParams.allow_short ?? false,
        leverage: backtestParams.leverage ?? 1,
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
      const modelUsed = genData.model_used || undefined

      addLogEntry({
        type: 'code-preview',
        content: strategyName,
        detail: scriptCode,
        iterationId,
      })

      setIterationHistory(prev => prev.map(n =>
        n.id === iterationId
          ? { ...n, scriptCode, scriptId, strategyName, modelUsed, status: 'executing' }
          : n
      ))

      setPhase('executing')

      const timeframe = overrideTimeframes?.[0] ?? backtestParams.timeframe
      const tfRunnerId = addLogEntry({
        type: 'ai-step',
        content: `Running ${timeframe}...`,
        status: 'active',
        startedAt: Date.now(),
        iterationId,
      })

      const outcome = await executeSingleTimeframe(
        scriptId, scriptCode, timeframe, iterationId, signal, overrideSymbol,
        directionId, directionIndex, directionPrompt, wfvConfig,
      )
      updateLogEntry(tfRunnerId, { status: 'done', completedAt: Date.now() })

      if (signal.aborted) return null

      if (outcome?.result) {
        const backtestResult = outcome.result

        // Apply liquidity cache: use first iteration's liquidity for all subsequent ones
        let finalRating = outcome.rating
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
        addLogEntry({
          type: 'complete',
          content: `${returnSign}${returnPct}% return, ${backtestResult.num_trades} trades, ${(backtestResult.win_rate * 100).toFixed(0)}% win rate, ${backtestResult.sharpe_ratio.toFixed(2)} sharpe`,
          iterationId,
        })

        const wfResult = outcome.walkForwardResult ?? null
        const metricsFields = {
          result: backtestResult,
          rating: finalRating,
          totalReturn: backtestResult.total_return,
          winRate: backtestResult.win_rate,
          numTrades: backtestResult.num_trades,
          sharpe: backtestResult.sharpe_ratio,
          maxDrawdown: backtestResult.max_drawdown,
          ...(wfResult ? { walkForwardStatus: 'complete' as const, walkForwardResult: wfResult } : {}),
        }
        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId ? { ...n, ...metricsFields } : n
        ))
        // Sync the ref immediately so startAutoRun can read the final metrics
        // before React re-renders and the useEffect syncs it.
        iterationHistoryRef.current = iterationHistoryRef.current.map(n =>
          n.id === iterationId ? { ...n, ...metricsFields } : n
        )

        setPhase('results')
        // isLoading stays true while insights are being fetched — the generate
        // button and auto-run remain disabled until the iteration is fully done.

        let newInsights: StrategyInsights | null = null

        if (!skipInsights) {
          const insightsStepId = addLogEntry({
            type: 'ai-step',
            content: 'Generating suggestions...',
            status: 'active',
            startedAt: Date.now(),
            iterationId,
          })

          try {
            const previousSummary = iterationHistoryRef.current
              .filter(n => n.status === 'complete' && n.id !== iterationId)
              .slice(-1)[0]?.insights?.summary ?? undefined

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
                timeframe: overrideTimeframes?.[0] ?? backtestParams.timeframe,
                start_date: backtestParams.start_date,
                end_date: backtestParams.end_date,
                allow_short: backtestParams.allow_short ?? false,
                leverage: backtestParams.leverage ?? 1,
                initial_capital: backtestParams.initial_capital,
                previous_summary: previousSummary,
              }),
              signal,
            })

            const insData = await insResponse.json()

            if (insData.success) {
              newInsights = {
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
            } else {
              updateLogEntry(insightsStepId, { status: 'done', completedAt: Date.now() })
            }
          } catch {
            updateLogEntry(insightsStepId, { status: 'done', completedAt: Date.now() })
          }
        }

        // Atomic: mark iteration complete (with insights if available) in one
        // render batch. This ensures the save that fires on status='complete'
        // always captures both backtest results and any suggestions together.
        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId
            ? { ...n, status: 'complete' as const, ...(newInsights ? { insights: newInsights } : {}) }
            : n
        ))
        iterationHistoryRef.current = iterationHistoryRef.current.map(n =>
          n.id === iterationId
            ? { ...n, status: 'complete' as const, ...(newInsights ? { insights: newInsights } : {}) }
            : n
        )
        // Auto-select for regular runs; skip for direction cards running in parallel
        if (!skipInsights) {
          setSelectedIterationId(iterationId)
        }
        setIsLoading(false)
        return iterationHistoryRef.current.find(n => n.id === iterationId) ?? null
      } else {
        const errMsg = 'Backtest failed'
        addLogEntry({ type: 'error', content: errMsg, iterationId })
        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId ? { ...n, status: 'error', error: errMsg } : n
        ))
        setError(errMsg)
        setPhase('idle')
        setIsLoading(false)
        return null
      }
    } catch (err) {
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
  }, [backtestParams, addLogEntry, updateLogEntry, executeSingleTimeframe])

  // ==========================================================================
  // deleteIteration
  // ==========================================================================

  const deleteIteration = useCallback((id: string) => {
    const getDescendants = (nodeId: string): string[] => {
      const children = iterationHistoryRef.current.filter(n => n.parentId === nodeId)
      return [nodeId, ...children.flatMap(c => getDescendants(c.id))]
    }
    const idsToDelete = getDescendants(id)
    setIterationHistory(prev => {
      const next = prev.filter(n => !idsToDelete.includes(n.id))
      if (next.length === 0) setPhase('idle')
      return next
    })
    setActivityLog(prev => prev.filter(e => !idsToDelete.includes(e.iterationId ?? '')))
    if (idsToDelete.includes(selectedIterationId ?? '')) setSelectedIterationId(null)
    idsToDelete.forEach(nodeId => {
      savedIterationVersionRef.current.delete(nodeId)
      deleteIterationFromStore(sessionId, nodeId)
    })
  }, [sessionId, selectedIterationId])

  // ==========================================================================
  // markSuggestionDisabled
  // ==========================================================================

  const markSuggestionDisabled = useCallback((iterationId: string, suggestionIdx: number) => {
    const updater = (prev: IterationNode[]) =>
      prev.map(n => {
        if (n.id !== iterationId || !n.insights) return n
        const suggestions = n.insights.suggestions.map((s, i) =>
          i === suggestionIdx ? { ...s, disabled: true } : s
        )
        return { ...n, insights: { ...n.insights, suggestions } }
      })
    setIterationHistory(updater)
    iterationHistoryRef.current = updater(iterationHistoryRef.current)

    // Keep the activity log entry in sync so the UI reflects the disabled state immediately.
    // Match by title (not global index) so second-batch entries (local indices 0–9) are found correctly.
    setActivityLog(prev => {
      const disabledTitle = iterationHistoryRef.current
        .find(n => n.id === iterationId)?.insights?.suggestions[suggestionIdx]?.title
      if (!disabledTitle) return prev
      return prev.map(e => {
        if (e.type !== 'insights' || e.iterationId !== iterationId || !e.detail) return e
        try {
          const sArr = JSON.parse(e.detail) as InsightsSuggestion[]
          const updated = sArr.map(s => s.title === disabledTitle ? { ...s, disabled: true } : s)
          if (updated.every((s, i) => s === sArr[i])) return e  // no change — skip re-render
          return { ...e, detail: JSON.stringify(updated) }
        } catch {
          return e
        }
      })
    })
  }, [])

  // ==========================================================================
  // selectIteration
  // ==========================================================================

  const selectIteration = useCallback((id: string | null) => {
    setSelectedIterationId(id)
  }, [])

  // Lazy-load one iteration's heavy detail (result/rating/insights/scriptCode/
  // prompt) and merge it into the in-memory node. Used for the selected run and
  // the initially-resolved run on session open, since the list/open path is now
  // lightweight.
  const loadIterationDetail = useCallback(async (id: string) => {
    const current = iterationHistoryRef.current.find(n => n.id === id)
    if (!current) return
    if (current.result) return                       // already have heavy detail
    if (loadingDetailIdRef.current === id) return     // fetch already in flight
    loadingDetailIdRef.current = id
    setDetailLoading(true)
    setDetailError(null)
    try {
      const detail = await fetchIterationDetail(sessionId, id) as Partial<IterationNode>
      const apply = (list: IterationNode[]) => list.map(n =>
        n.id === id
          ? {
              ...n,
              result: detail.result ?? null,
              rating: detail.rating ?? null,
              insights: detail.insights ?? n.insights ?? null,
              prompt: detail.prompt || n.prompt || '',
              scriptCode: detail.scriptCode || n.scriptCode || '',
              scriptId: detail.scriptId || n.scriptId || '',
              walkForwardResult: detail.walkForwardResult ?? n.walkForwardResult ?? null,
              walkForwardStatus: detail.walkForwardStatus ?? n.walkForwardStatus,
            }
          : n
      )
      const nextHistory = apply(iterationHistoryRef.current)
      const merged = nextHistory.find(n => n.id === id)
      // Prevent the save effect from re-persisting lazy-loaded detail: it keys
      // off `${status}:${insights?.suggestions?.length}`. The lightweight node
      // seeded `complete:0` at hydration; once real insights merge in, that key
      // would differ and trigger a redundant upsert of an already-stored
      // iteration. Pre-set the ref to the post-merge key so the effect no-ops.
      if (merged && (merged.status === 'complete' || merged.status === 'error')) {
        savedIterationVersionRef.current.set(
          id, `${merged.status}:${merged.insights?.suggestions?.length ?? 0}`
        )
      }
      iterationHistoryRef.current = nextHistory
      setIterationHistory(prev => apply(prev))
    } catch (e) {
      setDetailError(e instanceof Error ? e.message : 'Failed to load run detail')
    } finally {
      loadingDetailIdRef.current = null
      setDetailLoading(false)
    }
  }, [sessionId])

  // Fetch heavy detail for the selected (or initially-resolved) run when it is
  // still lightweight. Covers both session-open (resolved id) and user
  // selection from history.
  useEffect(() => {
    if (!isHydrated) return
    const id = selectedIterationId
    if (!id) return
    const node = iterationHistory.find(n => n.id === id)
    // Re-bind on every selection whose rendered node lacks heavy detail.
    // `node.result` is the authoritative "already have detail" signal;
    // loadingDetailIdRef dedupes an in-flight fetch (loadIterationDetail
    // re-checks both). This is what makes J-02 re-bind the RIGHT analysis
    // panel (trades/equity/WF) for a selected prior run instead of the
    // detail staying pinned to the latest run.
    if (!node || node.result || loadingDetailIdRef.current === id) return
    loadIterationDetail(id)
  }, [isHydrated, selectedIterationId, iterationHistory, loadIterationDetail])

  // Clear any stale detail error when the selection changes (a fresh selection
  // gets a fresh detail-pane state; loadIterationDetail sets its own error).
  useEffect(() => {
    setDetailError(null)
  }, [selectedIterationId])

  const retryDetailLoad = useCallback(() => {
    const id = selectedIterationIdRef.current
    if (id) loadIterationDetail(id)
  }, [loadIterationDetail])

  // ==========================================================================
  // loadCachedIteration — inject a pre-built node (from directions cache)
  // ==========================================================================

  const loadCachedIteration = useCallback((node: IterationNode) => {
    setIterationHistory(prev => {
      if (prev.some(n => n.id === node.id)) {
        return prev.map(n => n.id === node.id ? node : n)
      }
      return [...prev, node]
    })
    setSelectedIterationId(node.id)
    const idx = iterationHistoryRef.current.length + 1
    upsertIteration(sessionId, idx, node)
  }, [sessionId])

  const generateInsightsForIteration = useCallback(async (
    iterationId: string,
    model: string,
    previousSuggestions?: InsightsSuggestion[],
  ) => {
    const iteration = iterationHistoryRef.current.find(n => n.id === iterationId)
    if (!iteration?.result) return

    const timeframe = iteration.params?.timeframe ?? backtestParams.timeframe

    const insightsStepId = addLogEntry({
      type: 'ai-step',
      content: previousSuggestions ? 'Generating new batch of suggestions...' : 'Generating suggestions...',
      status: 'active',
      startedAt: Date.now(),
      iterationId,
    })

    try {
      const wfSummary = iteration.walkForwardStatus === 'complete' && iteration.walkForwardResult
        ? {
            wfe: iteration.walkForwardResult.wfe,
            num_windows: iteration.walkForwardResult.num_windows,
            combined_oos_return: iteration.walkForwardResult.combined_oos_return,
            combined_oos_sharpe: iteration.walkForwardResult.combined_oos_sharpe,
            combined_oos_win_rate: iteration.walkForwardResult.combined_oos_win_rate,
            combined_oos_max_drawdown: iteration.walkForwardResult.combined_oos_max_drawdown,
          }
        : undefined

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
          allow_short: backtestParams.allow_short ?? false,
          leverage: backtestParams.leverage ?? 1,
          initial_capital: backtestParams.initial_capital,
          ...(previousSuggestions && {
            previous_suggestions: previousSuggestions.map(s => s.title),
          }),
          ...(wfSummary && { walk_forward_result: wfSummary }),
        }),
      })
      const insData = await insResponse.json()
      if (insData.success) {
        // Compute next batchIndex
        const nextBatchIndex = previousSuggestions
          ? Math.max(0, ...previousSuggestions.map(s => s.batchIndex ?? 0)) + 1
          : 0

        // Tag new suggestions with batchIndex
        const newBatchSuggestions: InsightsSuggestion[] = (insData.suggestions || []).map(
          (s: InsightsSuggestion) => ({ ...s, batchIndex: nextBatchIndex })
        )

        updateLogEntry(insightsStepId, { status: 'done', completedAt: Date.now() })

        // Activity log entry shows ONLY the new batch's suggestions
        addLogEntry({
          type: 'insights',
          content: insData.summary || '',
          detail: JSON.stringify(newBatchSuggestions),
          iterationId,
        })

        // Combine: previous (all batches so far) + new batch
        const allSuggestions = previousSuggestions
          ? [...previousSuggestions, ...newBatchSuggestions]
          : newBatchSuggestions

        const newInsights: StrategyInsights = {
          summary: insData.summary || '',
          suggestions: allSuggestions,
        }
        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId ? { ...n, insights: newInsights } : n
        ))
        // Sync ref immediately so startAutoRun can read the new suggestions
        // on the very next loop iteration (before React re-renders).
        iterationHistoryRef.current = iterationHistoryRef.current.map(n =>
          n.id === iterationId ? { ...n, insights: newInsights } : n
        )
      } else {
        if (previousSuggestions) {
          updateLogEntry(insightsStepId, { status: 'error', completedAt: Date.now() })
          addLogEntry({
            type: 'error',
            content: `Failed to generate new suggestion batch: ${(insData.errors as string[] | undefined)?.join(', ') || 'API returned an error'}`,
            iterationId,
          })
        } else {
          updateLogEntry(insightsStepId, { status: 'done', completedAt: Date.now() })
        }
      }
    } catch (e) {
      if (previousSuggestions) {
        updateLogEntry(insightsStepId, { status: 'error', completedAt: Date.now() })
        addLogEntry({
          type: 'error',
          content: `Failed to generate new suggestion batch: ${e instanceof Error ? e.message : 'Unknown error'}`,
          iterationId,
        })
      } else {
        updateLogEntry(insightsStepId, { status: 'done', completedAt: Date.now() })
      }
    }
  }, [backtestParams, addLogEntry, updateLogEntry])

  const loadCachedAsStartingPoint = useCallback((node: IterationNode) => {
    addLogEntry({ type: 'user-prompt', content: node.prompt || `Loaded: ${node.strategyName}`, iterationId: node.id })
    addLogEntry({ type: 'code-preview', content: node.strategyName, iterationId: node.id })
    addLogEntry({ type: 'complete', content: `${node.strategyName} loaded from cache`, iterationId: node.id })
    if (node.insights?.suggestions?.length) {
      addLogEntry({
        type: 'insights',
        content: 'Suggestions from cached run:',
        detail: JSON.stringify(node.insights.suggestions),
        iterationId: node.id,
      })
    }
    setIterationHistory(prev => {
      if (prev.some(n => n.id === node.id)) return prev.map(n => n.id === node.id ? node : n)
      return [...prev, node]
    })
    setSelectedIterationId(node.id)
    const idx = iterationHistoryRef.current.length + 1
    upsertIteration(sessionId, idx, node)
    
    // Auto-generate insights if the cached run didn't have any
    if (!node.insights?.suggestions?.length) {
      // Need a small timeout to let the state settle so generateInsightsForIteration finds it
      setTimeout(() => {
        generateInsightsForIteration(node.id, node.modelUsed ?? FALLBACK_MODEL)
      }, 50)
    }
  }, [sessionId, addLogEntry, generateInsightsForIteration])

  const didAutoGenerateInsightsRef = useRef(false)
  useEffect(() => {
    if (didAutoGenerateInsightsRef.current) return
    didAutoGenerateInsightsRef.current = true
    const latest = [...iterationHistoryRef.current]
      .reverse()
      .find(n => n.status === 'complete' && !!n.result && !(n.insights?.suggestions?.length))
    if (latest) {
      generateInsightsForIteration(latest.id, latest.modelUsed ?? FALLBACK_MODEL)
    }
  }, [generateInsightsForIteration])

  // ==========================================================================
  // runWalkForward
  // ==========================================================================

  function _wfDownsample<T>(arr: T[], maxPoints: number): T[] {
    if (arr.length <= maxPoints) return arr
    const step = Math.ceil(arr.length / maxPoints)
    return arr.filter((_, i) => i % step === 0 || i === arr.length - 1)
  }

  function _trimWalkForwardForStorage(result: WalkForwardResult): WalkForwardResult {
    return {
      ...result,
      windows: result.windows.map(w => ({
        ...w,
        oos_equity_curve: _wfDownsample(w.oos_equity_curve, 100),
      })),
      combined_oos_equity: _wfDownsample(result.combined_oos_equity, 200),
    }
  }

  const runWalkForward = useCallback(async (
    iterationId: string,
    config: WalkForwardConfig,
    onProgress?: (window: number, total: number) => void,
  ): Promise<WalkForwardResult | null> => {
    const iteration = iterationHistoryRef.current.find(n => n.id === iterationId)
    if (!iteration || !iteration.params) return null

    // Set status to 'running'
    const markRunning = (prev: IterationNode[]) =>
      prev.map(n => n.id === iterationId
        ? { ...n, walkForwardStatus: 'running' as const, walkForwardResult: null }
        : n
      )
    setIterationHistory(markRunning)
    iterationHistoryRef.current = markRunning(iterationHistoryRef.current)

    try {
      const body = JSON.stringify({
        script_id: iteration.scriptId,
        script_code: iteration.scriptCode,
        symbol: iteration.params.symbol,
        timeframe: iteration.params.timeframe,
        start_date: iteration.params.start_date,
        end_date: iteration.params.end_date,
        initial_capital: iteration.params.initial_capital,
        commission: EXCHANGE_CONFIGS[iteration.params.exchange]?.commission ?? 0.00075,
        allow_short: iteration.params.allow_short ?? false,
        leverage: iteration.params.leverage ?? 1,
        is_months: config.isMonths,
        oos_months: config.oosMonths,
        ...(config.maxWindows !== undefined ? { max_windows: config.maxWindows } : {}),
      })

      const response = await fetch(`${API_BASE_URL}/api/execute-walk-forward`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      // Read SSE stream
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let finalData: any = null

      outer: while (!finalData) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''
        for (const part of parts) {
          for (const line of part.split('\n')) {
            if (!line.startsWith('data: ')) continue
            const event = JSON.parse(line.slice(6))
            if (event.type === 'status' && event.phase === 'walk_forward') {
              onProgress?.(event.wf_window ?? 0, event.wf_total ?? 0)
            } else if (event.type === 'result' || event.type === 'error') {
              finalData = event
              break outer
            }
          }
        }
      }
      reader.releaseLock()

      if (finalData?.type === 'result' && finalData.success) {
        const wfResult = _trimWalkForwardForStorage(finalData.result as WalkForwardResult)
        const markComplete = (prev: IterationNode[]) =>
          prev.map(n => n.id === iterationId
            ? { ...n, walkForwardStatus: 'complete' as const, walkForwardResult: wfResult }
            : n
          )
        setIterationHistory(markComplete)
        iterationHistoryRef.current = markComplete(iterationHistoryRef.current)

        // Persist the updated node
        const updatedNode = iterationHistoryRef.current.find(n => n.id === iterationId)
        const nodeIdx = iterationHistoryRef.current.findIndex(n => n.id === iterationId)
        if (updatedNode && nodeIdx >= 0) {
          upsertIteration(sessionId, nodeIdx + 1, updatedNode)
        }
        return wfResult
      } else {
        const markError = (prev: IterationNode[]) =>
          prev.map(n => n.id === iterationId
            ? { ...n, walkForwardStatus: 'error' as const }
            : n
          )
        setIterationHistory(markError)
        iterationHistoryRef.current = markError(iterationHistoryRef.current)
        return null
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return null
      const markError = (prev: IterationNode[]) =>
        prev.map(n => n.id === iterationId
          ? { ...n, walkForwardStatus: 'error' as const }
          : n
        )
      setIterationHistory(markError)
      iterationHistoryRef.current = markError(iterationHistoryRef.current)
      return null
    }
  }, [sessionId])

  // ==========================================================================
  // editAndRerun
  // ==========================================================================

  const editAndRerun = useCallback(async (originalIterationId: string, editedCode: string, model: string = FALLBACK_MODEL) => {
    const original = iterationHistory.find(n => n.id === originalIterationId)
    if (!original) return

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
      changeSummary: 'Re-run',
      params: { ...backtestParams },
      timestamp: new Date().toISOString(),
      status: 'executing',
      parentId: originalIterationId,
    }
    setIterationHistory(prev => [...prev, newIteration])

    try {
      const timeframe = backtestParams.timeframe
      const tfRunnerId = addLogEntry({
        type: 'ai-step',
        content: `Running ${timeframe}...`,
        status: 'active',
        startedAt: Date.now(),
        iterationId,
      })

      const wfvConfig: WalkForwardConfig = {
        isMonths: original.walkForwardResult?.is_months ?? 6,
        oosMonths: original.walkForwardResult?.oos_months ?? 3,
      }

      const outcome = await executeSingleTimeframe(
        original.scriptId, editedCode, timeframe, iterationId, signal,
        undefined, undefined, undefined, undefined, wfvConfig,
      )
      updateLogEntry(tfRunnerId, { status: 'done', completedAt: Date.now() })

      if (signal.aborted) return

      if (outcome?.result) {
        const backtestResult = outcome.result

        // Apply liquidity cache
        let finalRating = outcome.rating
        if (finalRating && cachedLiquidityRef.current) {
          finalRating = {
            ...finalRating,
            liquidity: cachedLiquidityRef.current.liquidity,
            capacity_levels: cachedLiquidityRef.current.capacity_levels,
          }
        }

        const wfResult = outcome.walkForwardResult ?? null

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
              rating: finalRating,
              totalReturn: backtestResult.total_return,
              winRate: backtestResult.win_rate,
              numTrades: backtestResult.num_trades,
              sharpe: backtestResult.sharpe_ratio,
              maxDrawdown: backtestResult.max_drawdown,
              status: 'complete',
              walkForwardStatus: wfResult ? 'complete' as const : undefined,
              walkForwardResult: wfResult ?? undefined,
            }
            : n
        ))

        // Sync the ref immediately so generateInsightsForIteration can read
        // iteration.result before the useEffect re-syncs after re-render.
        iterationHistoryRef.current = iterationHistoryRef.current.map(n =>
          n.id === iterationId
            ? { ...n, result: backtestResult, rating: finalRating, status: 'complete', walkForwardStatus: wfResult ? 'complete' as const : undefined, walkForwardResult: wfResult ?? undefined }
            : n
        )

        setPhase('results')
        setIsLoading(false)

        // Generate summary and suggestions — reads walkForwardResult from ref if WFV completed
        await generateInsightsForIteration(iterationId, model)
      } else {
        const errMsg = 'Backtest failed'
        addLogEntry({ type: 'error', content: errMsg, iterationId })
        setIterationHistory(prev => prev.map(n =>
          n.id === iterationId ? { ...n, status: 'error', error: errMsg } : n
        ))
        setError(errMsg)
        setPhase('idle')
        setIsLoading(false)
      }
    } catch (err) {
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
  }, [iterationHistory, backtestParams, addLogEntry, executeSingleTimeframe, generateInsightsForIteration, validateSymbolExists])

  const startAutoRun = useCallback(async (maxAttempts: number, model: string, fromIterationId: string) => {
    const baseline = iterationHistoryRef.current.find(n => n.id === fromIterationId)
    if (!baseline) return

    autoRunStopRef.current = false
    setIsAutoRunning(true)
    setAutoRunProgress({ current: 0, max: maxAttempts })

    const abortController = new AbortController()
    abortControllerRef.current = abortController
    const { signal } = abortController

    if (baseline.params) {
      setBacktestParams(baseline.params)
    }

    let baselineId = baseline.id
    let attempt = 0
    let generatedNewBatch = false

    while (attempt < maxAttempts && !autoRunStopRef.current) {
      const currentBaseline = iterationHistoryRef.current.find(n => n.id === baselineId)
      const suggestions = currentBaseline?.insights?.suggestions ?? []

      // Identify all untried suggestions
      const untriedSuggestions: Array<{
        suggestion: InsightsSuggestion
        index: number
      }> = []

      suggestions.forEach((s, idx) => {
        if (!s.disabled) {
          untriedSuggestions.push({ suggestion: s, index: idx })
        }
      })

      if (untriedSuggestions.length === 0) {
        if (suggestions.length === 0) break // No suggestions at all

        // All suggestions tried. Generate a new batch once per baseline.
        if (!generatedNewBatch) {
          addLogEntry({ type: 'auto-run', content: 'All suggestions tried — generating new batch...', iterationId: baselineId })
          await generateInsightsForIteration(baselineId, model, suggestions)
          generatedNewBatch = true
          const refreshed = iterationHistoryRef.current.find(n => n.id === baselineId)
          const refreshedSuggestions = refreshed?.insights?.suggestions ?? []

          if (refreshedSuggestions.filter(s => !s.disabled).length === 0) break // API failed to produce new suggestions
          continue
        }
        break // New batch was already generated and also exhausted — stop
      }

      const scoreIteration = (node: IterationNode): number => {
        const trades = node.numTrades ?? 0
        if (trades === 0) return -Infinity
        // Ramps from 0.5× at 1 trade → 1.0× at 50+ trades
        const freqMultiplier = Math.min(1, 0.5 + (trades / 100))
        const base = node.totalReturn ?? -Infinity
        const sharpeBonus = (node.sharpe ?? 0) > 0 ? (node.sharpe ?? 0) * 0.05 : 0
        return (base + sharpeBonus) * freqMultiplier
      }

      const baselineScore = scoreIteration(currentBaseline ?? {} as IterationNode)
      const fmt = (v: number) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(2)}%`

      const workers = workerCountRef.current
      const concurrencyNote = workers === 1 ? '1 at a time' : `${workers} at a time`
      addLogEntry({
        type: 'auto-run',
        content: `Running ${untriedSuggestions.length} suggestions (${concurrencyNote})...`,
        iterationId: baselineId
      })

      const baselineResult = currentBaseline?.result
      const metrics = baselineResult ? {
        total_return: baselineResult.total_return,
        max_drawdown: baselineResult.max_drawdown,
        num_trades: baselineResult.num_trades,
        win_rate: baselineResult.win_rate,
        sharpe_ratio: baselineResult.sharpe_ratio,
        profit_factor: baselineResult.profit_factor,
      } : null

      // Use a worker-pool semaphore so at most workerCount backtests run at once
      autoRunIterationIdsRef.current = new Set()
      const baselineWf = iterationHistoryRef.current.find(n => n.id === baselineId)?.walkForwardResult
      const wfvConfigForRun: WalkForwardConfig = {
        isMonths: baselineWf?.is_months ?? 6,
        oosMonths: baselineWf?.oos_months ?? 3,
      }

      const sem = createSemaphore(workers)
      const executionPromises = untriedSuggestions.map(async ({ suggestion, index }) => {
        await sem.acquire()
        try {
          const node = await generateAndExecute(
            suggestion.prompt, model, currentBaseline?.scriptCode, metrics,
            undefined, undefined, true, suggestion.title, signal,
            undefined, undefined, undefined, baselineId,
            currentBaseline?.params ?? undefined,
            wfvConfigForRun,
          )
          const id = node?.id ?? null
          if (id) autoRunIterationIdsRef.current.add(id)
          return { id, suggestion, index }
        } catch {
          return { id: null, suggestion, index }
        } finally {
          sem.release()
        }
      })

      const results = await Promise.all(executionPromises)

      if (autoRunStopRef.current || signal.aborted) {
        results.forEach(({ id }) => { if (id) deleteIteration(id) })
        break
      }

      let bestScore = -Infinity
      let bestId: string | null = null

      const finishedIds: string[] = []

      // Evaluate results
      results.forEach(({ id, index }) => {
        if (!id) {
          markSuggestionDisabled(baselineId, index)
          return
        }
        finishedIds.push(id)
        const newIteration = iterationHistoryRef.current.find(n => n.id === id)
        const newScore = newIteration ? scoreIteration(newIteration) : -Infinity

        if (newIteration?.status === 'complete' && newScore > bestScore) {
          bestScore = newScore
          bestId = id
        }
      })

      const WF_ACCEPT_THRESHOLD = 0.3

      if (bestId && bestScore > baselineScore) {
        // Read walk-forward result from inline WFV (ran as phase 5 of backtest)
        const bestIteration = iterationHistoryRef.current.find(n => n.id === bestId)
        const wfResult = bestIteration?.walkForwardResult ?? null

        if (wfResult && wfResult.wfe < WF_ACCEPT_THRESHOLD) {
          addLogEntry({
            type: 'auto-run',
            content: `Walk-forward rejected candidate (WFE ${wfResult.wfe.toFixed(2)} < ${WF_ACCEPT_THRESHOLD}) — discarding.`,
            iterationId: baselineId,
          })
          deleteIteration(bestId)
          untriedSuggestions.forEach(({ index }) => markSuggestionDisabled(baselineId, index))
          continue
        }

        attempt++
        setAutoRunProgress({ current: attempt, max: maxAttempts })
        addLogEntry({ type: 'auto-run', content: `Kept (${attempt}/${maxAttempts}): ${fmt(bestScore)} > ${fmt(baselineScore)} — generating suggestions...`, iterationId: bestId })

        // Delete all others
        finishedIds.forEach(id => {
          if (id !== bestId) deleteIteration(id)
        })

        // Disable all suggestions on the old baseline since we're moving on
        untriedSuggestions.forEach(({ index }) => markSuggestionDisabled(baselineId, index))

        baselineId = bestId
        generatedNewBatch = false
        await generateInsightsForIteration(bestId, model)
      } else {
        addLogEntry({
          type: 'auto-run',
          content: `All ${untriedSuggestions.length} concurrent runs failed to beat baseline (${fmt(baselineScore)}). Generating new batch...`,
          iterationId: baselineId,
        })

        // Delete all generated iterations since none beat the baseline
        finishedIds.forEach(id => deleteIteration(id))

        // Mark all as disabled
        untriedSuggestions.forEach(({ index }) => markSuggestionDisabled(baselineId, index))
      }
    }

    setIsAutoRunning(false)
    setAutoRunProgress(null)
    autoRunStopRef.current = false
    abortControllerRef.current = null

    const reason = attempt >= maxAttempts ? `${maxAttempts} improvements done` : 'no more suggestions'
    addLogEntry({ type: 'auto-run', content: `Auto Run finished — ${reason}`, iterationId: baselineId })
  }, [generateAndExecute, deleteIteration, markSuggestionDisabled, addLogEntry, generateInsightsForIteration])

  const stopAutoRun = useCallback(() => {
    autoRunStopRef.current = true
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setPhase('idle')
    setIsLoading(false)
    const toRemove = autoRunIterationIdsRef.current
    setIterationHistory(prev => prev.filter(n => !toRemove.has(n.id)))
    autoRunIterationIdsRef.current = new Set()
    setActivityLog(prev => prev.map(e =>
      (e.status === 'active' || e.status === 'pending')
        ? { ...e, status: 'done' as const, completedAt: Date.now() }
        : e
    ))
  }, [])

  return {
    isHydrated,
    phase,
    isLoading,
    error,
    backtestParams,
    setBacktestParams,
    activityLog,
    selectedIterationId,
    iterationHistory,
    detailLoading,
    detailError,
    retryDetailLoad,
    generateAndExecute,
    editAndRerun,
    cancelOperation,
    deleteIteration,
    selectIteration,
    loadCachedIteration,
    loadCachedAsStartingPoint,
    isAutoRunning,
    autoRunProgress,
    startAutoRun,
    stopAutoRun,
    runWalkForward,
    sessionStatus,
    workerCount,
    autoRun,
  }
}
