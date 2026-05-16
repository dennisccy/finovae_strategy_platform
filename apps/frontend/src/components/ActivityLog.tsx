import { useState, useEffect, useRef, useMemo, FormEvent } from 'react'
import { Send, Square, Sparkles, Play, StopCircle } from 'lucide-react'
import { ActivityLogEntry } from './ActivityLogEntry'
import { ActivityLogGroup } from './ActivityLogGroup'
import type { ActivityEntry } from '../hooks/useBacktest'
import { getStrategyPrompts, getShortStrategyPrompts, type StrategyCard } from '../data/strategyPrompts'
import type { DirectionCacheSummary, DirectionsCacheResult } from '../lib/directionsApi'
import { FALLBACK_MODEL, type ModelOption } from '../lib/modelsApi'

interface IterationGroup {
  iterationId: string
  entries: ActivityEntry[]
  isComplete: boolean
  isError: boolean
  summary: string | null     // from 'complete' or 'error' entry
  prompt: string | null       // from 'user-prompt' entry
  strategyName: string | null // from 'code-preview' entry
}

function groupByIteration(entries: ActivityEntry[]): { groups: IterationGroup[]; ungrouped: ActivityEntry[] } {
  const groupMap = new Map<string, ActivityEntry[]>()
  const ungrouped: ActivityEntry[] = []

  for (const entry of entries) {
    if (entry.iterationId) {
      const list = groupMap.get(entry.iterationId)
      if (list) list.push(entry)
      else groupMap.set(entry.iterationId, [entry])
    } else {
      ungrouped.push(entry)
    }
  }

  const groups: IterationGroup[] = []
  for (const [iterationId, groupEntries] of groupMap) {
    const completeEntry = groupEntries.find(e => e.type === 'complete')
    const errorEntry = groupEntries.find(e => e.type === 'error')
    const promptEntry = groupEntries.find(e => e.type === 'user-prompt')
    const codeEntry = groupEntries.find(e => e.type === 'code-preview')

    groups.push({
      iterationId,
      entries: groupEntries,
      isComplete: !!completeEntry,
      isError: !!errorEntry && !completeEntry,
      summary: completeEntry?.content ?? errorEntry?.content ?? null,
      prompt: promptEntry?.content ?? null,
      strategyName: codeEntry?.content ?? null,
    })
  }

  return { groups, ungrouped }
}


interface ActivityLogProps {
  entries: ActivityEntry[]
  onSubmitPrompt: (prompt: string, model: string) => void
  currentSymbol: string
  currentTimeframe: string
  isLoading: boolean
  onEditAndRerun: (iterationId: string) => void
  onSuggestionClick?: (prompt: string, title?: string) => void
  onCancel?: () => void
  allowShort?: boolean
  // Directions cache (v1.0)
  cacheResult?: DirectionsCacheResult | null
  isRunningAll?: boolean
  runAllProgress?: { current: number; total: number } | null
  concurrency?: number
  onConcurrencyChange?: (n: number) => void
  onRunAll?: (cards: StrategyCard[]) => void
  onStopRunAll?: () => void
  onCachedDirectionClick?: (card: StrategyCard, summary: DirectionCacheSummary) => void
  availableModels?: ModelOption[]
}

export function ActivityLog({ entries, onSubmitPrompt, currentSymbol, currentTimeframe, isLoading, onEditAndRerun, onSuggestionClick, onCancel, allowShort, cacheResult, isRunningAll, runAllProgress, concurrency = 10, onConcurrencyChange, onRunAll, onStopRunAll, onCachedDirectionClick, availableModels = [] }: ActivityLogProps) {
  const [prompt, setPrompt] = useState('')
  const [model, setModel] = useState(FALLBACK_MODEL)
  // When the async model list arrives, switch to the backend default unless the
  // current selection is already a valid option the user picked.
  useEffect(() => {
    if (availableModels.length === 0) return
    setModel(prev =>
      availableModels.some(m => m.value === prev)
        ? prev
        : (availableModels.find(m => m.default)?.value ?? availableModels[0].value)
    )
  }, [availableModels])
  const scrollRef = useRef<HTMLDivElement>(null)
  const isUserScrolledUp = useRef(false)
  const lastScrollHeight = useRef(0)
  const prevLengthRef = useRef(entries.length)

  // Auto-scroll to bottom on new or updated entries
  useEffect(() => {
    const element = scrollRef.current
    if (!element) return

    const isNewEntry = entries.length > prevLengthRef.current
    prevLengthRef.current = entries.length

    // Always scroll when a new message is added;
    // only scroll on content updates if user hasn't scrolled away
    if (isNewEntry || !isUserScrolledUp.current) {
      element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' })
      lastScrollHeight.current = element.scrollHeight
    }
  }, [entries])

  // Detect user scroll to prevent auto-scroll interruption
  useEffect(() => {
    const element = scrollRef.current
    if (!element) return

    const handleScroll = () => {
      const isAtBottom = element.scrollHeight - element.scrollTop - element.clientHeight < 50
      isUserScrolledUp.current = !isAtBottom

      // Re-enable auto-scroll after 2s if user scrolls to bottom
      if (isAtBottom) {
        setTimeout(() => {
          isUserScrolledUp.current = false
        }, 2000)
      }
    }

    element.addEventListener('scroll', handleScroll)
    return () => element.removeEventListener('scroll', handleScroll)
  }, [])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!prompt.trim() || isLoading) return
    onSubmitPrompt(prompt, model)
    setPrompt('')
  }

  const handleRecommendClick = (card: StrategyCard) => {
    if (isLoading) return
    onSubmitPrompt(card.prompt, model)
  }

  const handleCardClick = (card: StrategyCard) => {
    const summary = cacheResult?.directions.find(d => d.directionId === card.id)
    if (summary && summary.status === 'complete' && onCachedDirectionClick) {
      onCachedDirectionClick(card, summary)
    } else {
      handleRecommendClick(card)
    }
  }

  const cards = useMemo(
    () => allowShort
      ? getShortStrategyPrompts(currentSymbol, currentTimeframe)
      : getStrategyPrompts(currentSymbol, currentTimeframe),
    [currentSymbol, currentTimeframe, allowShort]
  )

  const isEmpty = entries.length === 0

  // Group entries by iteration: past iterations get collapsed, latest stays expanded
  const { groups, ungrouped } = useMemo(() => groupByIteration(entries), [entries])
  const latestIterationId = groups.length > 0 ? groups[groups.length - 1].iterationId : null

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Scrollable message area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 lg:p-6">
        {isEmpty ? (
          <div className="h-full flex flex-col justify-center">
            <div className="text-center mb-4">
              <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <Sparkles className="w-6 h-6 text-primary-500" />
              </div>
              <h3 className="text-base font-semibold text-slate-800">Strategy Builder</h3>
              <p className="text-sm text-slate-500 mt-1">
                {allowShort ? '20 long/short strategies for' : '20 strategies for'}{' '}
                <span className="font-medium text-slate-700">
                  {currentSymbol.replace('USDT', '')}/USDT · {currentTimeframe}
                </span>
              </p>
            </div>

            {/* Run All controls */}
            <div className="flex items-center gap-2 mb-4 flex-wrap">
              {isRunningAll ? (
                <>
                  <button
                    type="button"
                    onClick={onStopRunAll}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 text-white text-xs font-medium rounded-lg hover:bg-red-700 transition-colors flex-shrink-0"
                  >
                    <StopCircle className="w-3.5 h-3.5" />
                    Stop
                  </button>
                  {runAllProgress && (
                    <span className="text-xs text-slate-500 font-medium">
                      {runAllProgress.current}/{runAllProgress.total} complete
                    </span>
                  )}
                </>
              ) : (
                <>
                  <button
                    type="button"
                    disabled={isLoading}
                    onClick={() => onRunAll?.(cards)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-600 text-white text-xs font-medium rounded-lg hover:bg-primary-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex-shrink-0"
                  >
                    <Play className="w-3.5 h-3.5" />
                    Run All
                  </button>
                  <label className="flex items-center gap-1.5 text-xs text-slate-500 flex-shrink-0">
                    <span>Parallel</span>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={concurrency}
                      onChange={e => onConcurrencyChange?.(Math.max(1, Math.min(20, Number(e.target.value))))}
                      className="w-12 px-1.5 py-0.5 text-xs border border-slate-200 rounded text-center focus:ring-1 focus:ring-primary-500 focus:border-transparent"
                    />
                  </label>
                  {cacheResult?.cached && (
                    <span className="text-xs text-emerald-600 font-medium">
                      {cacheResult.directions.filter(d => d.status === 'complete').length}/{cards.length} cached
                    </span>
                  )}
                </>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 lg:gap-3">
              {cards.map((card) => {
                const cached = cacheResult?.directions.find(d => d.directionId === card.id)
                const isCachedComplete = cached?.status === 'complete'
                const isCachedError = cached?.status === 'error'
                return (
                  <button
                    key={card.id}
                    type="button"
                    disabled={isLoading && !isCachedComplete}
                    onClick={() => handleCardClick(card)}
                    className={`text-left p-3 border rounded-xl transition-colors ${
                      isCachedComplete
                        ? 'border-emerald-200 hover:border-emerald-400 hover:bg-emerald-50'
                        : isCachedError
                          ? 'border-red-200 hover:border-red-300 hover:bg-red-50'
                          : 'border-slate-200 hover:border-primary-300 hover:bg-primary-50'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    <div className="mb-1.5 flex items-center gap-1.5 flex-wrap">
                      <span className={`text-xs px-1.5 py-0.5 border rounded font-medium ${
                        isCachedComplete
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : isCachedError
                            ? 'bg-red-50 text-red-600 border-red-200'
                            : 'bg-primary-50 text-primary-600 border-primary-100'
                      }`}>
                        {card.title}
                      </span>
                      {isCachedComplete && cached && (
                        <>
                          <span className={`text-xs font-semibold ${(cached.totalReturn ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                            {(cached.totalReturn ?? 0) >= 0 ? '+' : ''}{((cached.totalReturn ?? 0) * 100).toFixed(1)}%
                          </span>
                          <span className="text-xs text-slate-400">{cached.numTrades ?? 0}T</span>
                          <span className="text-xs text-slate-400">SR {(cached.sharpe ?? 0).toFixed(2)}</span>
                        </>
                      )}
                      {isCachedError && (
                        <span className="text-xs text-red-500 font-medium">Error</span>
                      )}
                    </div>
                    <span className="block mt-1 text-xs text-slate-500 leading-relaxed">{card.tagline}</span>
                  </button>
                )
              })}
            </div>
          </div>
        ) : (
          <div>
            {/* Ungrouped entries (no iterationId) */}
            {ungrouped.map((entry) => (
              <ActivityLogEntry
                key={entry.id}
                entry={entry}
                onEditAndRerun={onEditAndRerun}
                onSuggestionClick={onSuggestionClick}
              />
            ))}
            {/* Iteration groups: wrapped in accordion components */}
            {groups.map((group) => {
              const isLatest = group.iterationId === latestIterationId
              // If we have multiple groups and it's not the latest one, collapse it by default.
              // Otherwise (e.g., standard sequential UX), keep it expanded.
              const defaultExpanded = isLatest && groups.length < 5

              return (
                <ActivityLogGroup
                  key={group.iterationId}
                  iterationId={group.iterationId}
                  entries={group.entries}
                  isComplete={group.isComplete}
                  isError={group.isError}
                  summary={group.summary}
                  prompt={group.prompt}
                  strategyName={group.strategyName}
                  onEditAndRerun={onEditAndRerun}
                  onSuggestionClick={onSuggestionClick}
                  suggestionsDisabled={!isLatest}
                  defaultExpanded={defaultExpanded}
                />
              )
            })}
          </div>
        )}
      </div>

      {/* Sticky bottom: model selector + input */}
      <div className="border-t border-slate-200 p-3 lg:p-4 bg-white flex-shrink-0">
        <div className="flex items-center gap-2 mb-2">
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="px-2 py-1 text-xs border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
          >
            {availableModels.map(m => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit(e)
              }
            }}
            placeholder="Describe a trading strategy..."
            disabled={isLoading}
            rows={1}
            className="flex-1 px-3 py-2 text-sm border border-slate-200 rounded-lg resize-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-slate-50 disabled:cursor-not-allowed chat-input"
          />
          {isLoading ? (
            <button
              type="button"
              onClick={onCancel}
              className="px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex-shrink-0"
              title="Stop operation"
            >
              <Square className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!prompt.trim()}
              className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex-shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </form>
      </div>
    </div>
  )
}
