import { useState, useCallback } from 'react'

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
}

export interface RunHistoryItem {
  run_id: string
  timestamp: string
  natural_language: string
  total_return: number
  num_trades: number
}

export function useBacktest() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [strategySpec, setStrategySpec] = useState<StrategySpec | null>(null)
  const [runHistory, setRunHistory] = useState<RunHistoryItem[]>([])

  const runBacktest = useCallback(async (request: BacktestRequest) => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/run-backtest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
      setStrategySpec(data.strategy_spec)

      // Add to run history
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

  return {
    isLoading,
    error,
    result,
    strategySpec,
    runHistory,
    runBacktest,
  }
}
