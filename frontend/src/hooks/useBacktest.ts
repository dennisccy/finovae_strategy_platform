import { useState, useCallback } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

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

export type Phase = 'idle' | 'generating' | 'review' | 'executing' | 'results'

export function useBacktest() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [strategySpec, setStrategySpec] = useState<StrategySpec | null>(null)
  const [runHistory, setRunHistory] = useState<RunHistoryItem[]>([])
  const [rating, setRating] = useState<StrategyRating | null>(null)
  const [generatedScript, setGeneratedScript] = useState<GeneratedScript | null>(null)
  const [scriptCode, setScriptCode] = useState<string | null>(null)
  const [insights, setInsights] = useState<StrategyInsights | null>(null)
  const [insightsLoading, setInsightsLoading] = useState(false)

  const generateStrategy = useCallback(async (naturalLanguage: string, model: string, previousScriptCode?: string) => {
    setPhase('generating')
    setIsLoading(true)
    setError(null)

    try {
      const body: Record<string, string> = { natural_language: naturalLanguage, model }
      if (previousScriptCode) {
        body.previous_script_code = previousScriptCode
      }

      const response = await fetch(`${API_BASE_URL}/api/generate-strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      const data = await response.json()

      if (!data.success) {
        setError(data.errors?.join(', ') || 'Strategy generation failed')
        setPhase('idle')
        return
      }

      const script: GeneratedScript = {
        script_id: data.script_id,
        script_code: data.script_code,
        strategy_name: data.strategy_name,
        strategy_description: data.strategy_description,
        validation_errors: data.validation_errors || [],
      }

      setGeneratedScript(script)
      setScriptCode(data.script_code)
      setPhase('review')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate strategy')
      setPhase('idle')
    } finally {
      setIsLoading(false)
    }
  }, [])

  const executeBacktest = useCallback(async (params: {
    script_id: string
    script_code?: string
    symbol: string
    timeframe: string
    start_date: string
    end_date: string
    initial_capital: number
  }) => {
    setPhase('executing')
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/execute-backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      })

      const data = await response.json()

      if (!data.success) {
        setError(data.errors?.join(', ') || 'Backtest execution failed')
        setPhase('review')
        return
      }

      setResult(data.result)
      setRating(data.rating || null)
      setStrategySpec(null) // script-based runs don't have a StrategySpec
      setPhase('results')

      if (data.result) {
        setRunHistory(prev => [
          {
            run_id: data.result.run_id,
            timestamp: new Date().toISOString(),
            natural_language: generatedScript?.strategy_name || 'Script Strategy',
            total_return: data.result.total_return,
            num_trades: data.result.num_trades,
          },
          ...prev,
        ])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute backtest')
      setPhase('review')
    } finally {
      setIsLoading(false)
    }
  }, [generatedScript])

  // Legacy: old single-step flow (backward compat)
  const runBacktest = useCallback(async (request: BacktestRequest) => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/run-backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      })

      const data = await response.json()

      if (!data.success) {
        setError(data.errors?.join(', ') || 'Backtest failed')
        setResult(null)
        setStrategySpec(null)
        return
      }

      setResult(data.result)
      setRating(data.rating || null)
      setStrategySpec(data.strategy_spec)
      setPhase('results')

      if (data.result) {
        setRunHistory(prev => [
          {
            run_id: data.result.run_id,
            timestamp: new Date().toISOString(),
            natural_language: request.natural_language,
            total_return: data.result.total_return,
            num_trades: data.result.num_trades,
          },
          ...prev,
        ])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run backtest')
      setResult(null)
      setStrategySpec(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const generateInsights = useCallback(async (model: string = 'claude-haiku-4-5-20251001') => {
    if (!result || !scriptCode) return

    setInsightsLoading(true)

    try {
      const response = await fetch(`${API_BASE_URL}/api/generate-insights`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          backtest_result: result,
          strategy_name: generatedScript?.strategy_name || '',
          strategy_description: generatedScript?.strategy_description || '',
          script_code: scriptCode,
          model,
        }),
      })

      const data = await response.json()

      if (data.success) {
        setInsights({
          summary: data.summary || '',
          suggestions: data.suggestions || [],
        })
      }
    } catch {
      // Insights are non-critical; silently fail
    } finally {
      setInsightsLoading(false)
    }
  }, [result, scriptCode, generatedScript])

  const resetToIdle = useCallback(() => {
    setPhase('idle')
    setError(null)
    setGeneratedScript(null)
    setScriptCode(null)
    setInsights(null)
  }, [])

  const backToReview = useCallback(() => {
    setPhase('review')
    setError(null)
  }, [])

  return {
    phase,
    isLoading,
    error,
    result,
    rating,
    strategySpec,
    runHistory,
    generatedScript,
    scriptCode,
    setScriptCode,
    insights,
    insightsLoading,
    generateStrategy,
    generateInsights,
    executeBacktest,
    runBacktest,
    resetToIdle,
    backToReview,
  }
}
