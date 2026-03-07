/**
 * API client for the directions cache endpoints.
 * Handles GET/POST /api/directions/cache and GET /api/directions/cache/{id}.
 */

import type { BacktestParams, IterationNode } from '../hooks/useBacktest'

const API_BASE = import.meta.env.VITE_API_URL || ''

export interface DirectionCacheSummary {
  directionId: string
  title: string
  tagline: string
  totalReturn: number
  winRate: number
  numTrades: number
  sharpe: number
  maxDrawdown: number
  status: 'complete' | 'error'
}

export interface DirectionsCacheResult {
  cached: boolean
  directions: DirectionCacheSummary[]
}

function buildQueryParams(params: BacktestParams): URLSearchParams {
  const p = new URLSearchParams({
    symbol: params.symbol,
    timeframe: params.timeframe,
    start_date: params.start_date,
    end_date: params.end_date,
    exchange: params.exchange,
    allow_short: String(params.allow_short ?? false),
    leverage: String(params.leverage ?? 1),
  })
  return p
}

export async function fetchDirectionsCache(
  params: BacktestParams
): Promise<DirectionsCacheResult> {
  try {
    const qs = buildQueryParams(params)
    const res = await fetch(`${API_BASE}/api/directions/cache?${qs}`)
    if (!res.ok) return { cached: false, directions: [] }
    return await res.json()
  } catch {
    return { cached: false, directions: [] }
  }
}

export async function fetchCachedDirection(
  params: BacktestParams,
  directionId: string
): Promise<IterationNode | null> {
  try {
    const qs = buildQueryParams(params)
    const res = await fetch(`${API_BASE}/api/directions/cache/${encodeURIComponent(directionId)}?${qs}`)
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export async function saveCachedDirection(
  params: BacktestParams,
  index: number,
  directionId: string,
  node: IterationNode
): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/directions/cache`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol: params.symbol,
        timeframe: params.timeframe,
        start_date: params.start_date,
        end_date: params.end_date,
        exchange: params.exchange,
        allow_short: params.allow_short ?? false,
        leverage: params.leverage ?? 1,
        index,
        direction_id: directionId,
        node,
      }),
    })
  } catch (e) {
    console.warn('[directionsApi] saveCachedDirection failed:', e)
  }
}
