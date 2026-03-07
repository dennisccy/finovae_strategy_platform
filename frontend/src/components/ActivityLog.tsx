import { useState, useEffect, useRef, useMemo, FormEvent } from 'react'
import { Send, Square, Sparkles } from 'lucide-react'
import { ActivityLogEntry } from './ActivityLogEntry'
import { ActivityLogGroup } from './ActivityLogGroup'
import type { ActivityEntry } from '../hooks/useBacktest'
import { getStrategyPrompts, getShortStrategyPrompts, type StrategyCard } from '../data/strategyPrompts'

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
}

export function ActivityLog({ entries, onSubmitPrompt, currentSymbol, currentTimeframe, isLoading, onEditAndRerun, onSuggestionClick, onCancel, allowShort }: ActivityLogProps) {
  const [prompt, setPrompt] = useState('')
  const [model, setModel] = useState('gpt-5-mini')
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
            <div className="text-center mb-6">
              <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <Sparkles className="w-6 h-6 text-primary-500" />
              </div>
              <h3 className="text-base font-semibold text-slate-800">Strategy Builder</h3>
              <p className="text-sm text-slate-500 mt-1">
                {allowShort ? '10 long/short strategies for' : '10 strategies for'}{' '}
                <span className="font-medium text-slate-700">
                  {currentSymbol.replace('USDT', '')}/USDT · {currentTimeframe}
                </span>
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 lg:gap-3">
              {cards.map((card) => (
                <button
                  key={card.id}
                  type="button"
                  disabled={isLoading}
                  onClick={() => handleRecommendClick(card)}
                  className="text-left p-3 border border-slate-200 rounded-xl hover:border-primary-300 hover:bg-primary-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <div className="mb-1.5">
                    <span className="text-xs px-1.5 py-0.5 bg-primary-50 text-primary-600 border border-primary-100 rounded font-medium">
                      {card.title}
                    </span>
                  </div>
                  <span className="block mt-1.5 text-xs text-slate-500 leading-relaxed">{card.tagline}</span>
                </button>
              ))}
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
            <option value="claude-haiku-4-5-20251001">Haiku 4.5</option>
            <option value="claude-sonnet-4-5-20250929">Sonnet 4.5</option>
            <option value="claude-sonnet-4-6">Sonnet 4.6</option>
            <option value="claude-opus-4-6">Opus 4.6</option>
            <option value="gpt-5-mini">GPT-5 Mini</option>
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
