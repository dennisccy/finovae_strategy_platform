import { useState, useEffect, useRef, useMemo, FormEvent } from 'react'
import { Send, Loader2, Sparkles, CheckCircle2, AlertCircle, ChevronDown, ChevronRight } from 'lucide-react'
import { ActivityLogEntry } from './ActivityLogEntry'
import type { ActivityEntry } from '../hooks/useBacktest'

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

function CollapsedIteration({ group, onEditAndRerun }: {
  group: IterationGroup
  onEditAndRerun?: (iterationId: string) => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="mb-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 transition-colors text-left group"
      >
        {group.isComplete && (
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
        )}
        {group.isError && (
          <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <span className="text-xs font-medium text-slate-700 truncate block">
            {group.strategyName || group.prompt || 'Iteration'}
          </span>
          {group.summary && (
            <span className="text-xs text-slate-400 truncate block">
              {group.summary}
            </span>
          )}
        </div>
        {expanded
          ? <ChevronDown className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
          : <ChevronRight className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
        }
      </button>
      {expanded && (
        <div className="mt-1 pl-2 border-l-2 border-slate-200 ml-3">
          {group.entries.map(entry => (
            <ActivityLogEntry
              key={entry.id}
              entry={entry}
              onEditAndRerun={onEditAndRerun}
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface RecommendCard {
  id: string
  title: string
  description: string
  prompt: string
}

const recommendCards: RecommendCard[] = [
  {
    id: 'multi-factor',
    title: 'Multi-Factor Quantitative',
    description: 'Combines momentum, trend, and volatility signals. Each factor must confirm before entering.',
    prompt: 'Build a quantitative multi-factor trading strategy that combines momentum, trend, and volatility technical dimensions to generate buy/sell signals. Each factor should confirm the others before entering, making the strategy more robust than any single indicator.',
  },
  {
    id: 'momentum-trend',
    title: 'Momentum Trend Following',
    description: 'Identifies and rides sustained price movements, entering on confirmed breakouts.',
    prompt: 'Build a trend-following trading strategy that identifies and rides sustained price movements. Enter on confirmed trend breakouts and exit when the trend weakens or reverses.',
  },
  {
    id: 'volatility-breakout',
    title: 'Volatility Breakout',
    description: 'Detects low-volatility consolidation and enters when price breaks out.',
    prompt: 'Build a volatility breakout trading strategy that detects low-volatility consolidation phases and enters when price breaks out of the consolidation range to capture the ensuing explosive move.',
  },
  {
    id: 'volume-momentum',
    title: 'Volume Momentum',
    description: 'Uses volume expansion to confirm price momentum direction.',
    prompt: 'Build a volume momentum trading strategy that uses volume expansion to confirm price momentum direction. Enter when price and volume expand together, and exit when volume contracts or diverges.',
  },
]

interface ActivityLogProps {
  entries: ActivityEntry[]
  onSubmitPrompt: (prompt: string, model: string) => void
  isLoading: boolean
  onEditAndRerun: (iterationId: string) => void
  onSuggestionClick?: (prompt: string) => void
}

export function ActivityLog({ entries, onSubmitPrompt, isLoading, onEditAndRerun, onSuggestionClick }: ActivityLogProps) {
  const [prompt, setPrompt] = useState('')
  const [model, setModel] = useState('claude-haiku-4-5-20251001')
  const scrollRef = useRef<HTMLDivElement>(null)
  const isUserScrolledUp = useRef(false)
  const lastScrollHeight = useRef(0)

  // Auto-scroll to bottom on new or updated entries (smooth behavior)
  useEffect(() => {
    if (scrollRef.current && !isUserScrolledUp.current) {
      const element = scrollRef.current
      const isAtBottom = element.scrollHeight - element.scrollTop - element.clientHeight < 50

      if (isAtBottom || lastScrollHeight.current !== element.scrollHeight) {
        element.scrollTo({
          top: element.scrollHeight,
          behavior: 'smooth'
        })
        lastScrollHeight.current = element.scrollHeight
      }
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

  const handleRecommendClick = (cardPrompt: string) => {
    if (isLoading) return
    onSubmitPrompt(cardPrompt, model)
  }

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
                Describe your trading strategy in plain English
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 lg:gap-3">
              {recommendCards.map((card) => (
                <button
                  key={card.id}
                  type="button"
                  disabled={isLoading}
                  onClick={() => handleRecommendClick(card.prompt)}
                  className="text-left p-3 border border-slate-200 rounded-xl hover:border-primary-300 hover:bg-primary-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <span className="block text-sm font-semibold text-slate-800">{card.title}</span>
                  <span className="block mt-1 text-xs text-slate-500 leading-relaxed">{card.description}</span>
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
            {/* Iteration groups: past collapsed, latest expanded */}
            {groups.map((group) => {
              const isPast = group.iterationId !== latestIterationId && (group.isComplete || group.isError)

              if (isPast) {
                return (
                  <CollapsedIteration
                    key={group.iterationId}
                    group={group}
                    onEditAndRerun={onEditAndRerun}
                  />
                )
              }

              // Latest / active iteration: render all entries fully
              return group.entries.map((entry) => (
                <ActivityLogEntry
                  key={entry.id}
                  entry={entry}
                  onEditAndRerun={onEditAndRerun}
                  onSuggestionClick={onSuggestionClick}
                />
              ))
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
          <button
            type="submit"
            disabled={!prompt.trim() || isLoading}
            className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
