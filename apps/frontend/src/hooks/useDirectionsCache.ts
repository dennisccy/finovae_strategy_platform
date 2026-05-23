/**
 * Hook for managing the directions cache:
 *   - Checks cache on param changes
 *   - Runs all directions with configurable concurrency
 *   - Saves completed results to cache after each run
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import type { BacktestParams, IterationNode } from './useBacktest'
import type { StrategyCard } from '../data/strategyPrompts'
import {
  fetchDirectionsCache,
  type DirectionsCacheResult,
  type DirectionCacheSummary,
} from '../lib/directionsApi'

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

export type RunOneCard = (card: StrategyCard, signal: AbortSignal) => Promise<IterationNode | null>

export interface RunAllProgress {
  current: number
  total: number
}

export function useDirectionsCache(backtestParams: BacktestParams) {
  const [cacheResult, setCacheResult] = useState<DirectionsCacheResult | null>(null)
  const [isCheckingCache, setIsCheckingCache] = useState(false)
  const [isRunningAll, setIsRunningAll] = useState(false)
  const [runAllProgress, setRunAllProgress] = useState<RunAllProgress | null>(null)
  const [concurrency, setConcurrency] = useState(10)

  const stopRef = useRef(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  const checkCache = useCallback(async () => {
    setIsCheckingCache(true)
    const result = await fetchDirectionsCache(backtestParams)
    setCacheResult(result)
    setIsCheckingCache(false)
  }, [backtestParams])

  // Check cache whenever params change
  useEffect(() => {
    checkCache()
  }, [checkCache])

  const runAllDirections = useCallback(async (
    cards: StrategyCard[],
    runOneCard: RunOneCard,
  ) => {
    if (isRunningAll) return

    // Only run directions that are not already cached as complete
    const cachedCompleteIds = new Set(
      (cacheResult?.directions ?? [])
        .filter(d => d.status === 'complete')
        .map(d => d.directionId)
    )
    const toRun = cards.filter(c => !cachedCompleteIds.has(c.id))

    if (toRun.length === 0) return

    setIsRunningAll(true)
    stopRef.current = false
    setRunAllProgress({ current: 0, total: toRun.length })

    const abortController = new AbortController()
    abortControllerRef.current = abortController
    const signal = abortController.signal

    const sem = createSemaphore(concurrency)
    let completed = 0

    const tasks = toRun.map(async (card) => {
      await sem.acquire()
      if (stopRef.current || signal.aborted) {
        sem.release()
        return
      }
      try {
        const node = await runOneCard(card, signal)
        if (node && !stopRef.current && !signal.aborted) {
          // Real-time badge update — cache was already saved atomically by the API
          setCacheResult(prev => {
            const newSummary: DirectionCacheSummary = {
              directionId: card.id,
              title: card.title,
              tagline: card.tagline,
              totalReturn: node.result?.total_return ?? 0,
              winRate: node.result?.win_rate ?? 0,
              numTrades: node.result?.num_trades ?? 0,
              sharpe: node.result?.sharpe_ratio ?? 0,
              maxDrawdown: node.result?.max_drawdown ?? 0,
              status: node.status === 'complete' ? 'complete' : 'error',
            }
            const directions = prev?.directions ?? []
            const idx = directions.findIndex(d => d.directionId === card.id)
            const newDirections = idx >= 0
              ? directions.map((d, i) => i === idx ? newSummary : d)
              : [...directions, newSummary]
            return { cached: true, directions: newDirections }
          })
        }
      } finally {
        sem.release()
        completed++
        setRunAllProgress({ current: completed, total: toRun.length })
      }
    })

    await Promise.all(tasks)

    // Refresh cache summary after all done
    if (!stopRef.current) {
      await checkCache()
    }

    setIsRunningAll(false)
    setRunAllProgress(null)
    stopRef.current = false
    abortControllerRef.current = null
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRunningAll, cacheResult, concurrency, backtestParams, checkCache])

  const stopRunAll = useCallback(() => {
    stopRef.current = true
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setIsRunningAll(false)
    setRunAllProgress(null)
  }, [])

  return {
    cacheResult,
    isCheckingCache,
    isRunningAll,
    runAllProgress,
    concurrency,
    setConcurrency,
    runAllDirections,
    stopRunAll,
    checkCache,
  }
}
