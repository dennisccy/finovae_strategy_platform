import { useState, useMemo, useEffect } from 'react'
import { ChevronDown, ChevronRight, Loader2, CheckCircle2, AlertCircle, Sparkles, Terminal } from 'lucide-react'
import type { ActivityEntry } from '../hooks/useBacktest'
import { ActivityLogEntry } from './ActivityLogEntry'

interface ActivityLogGroupProps {
    iterationId: string
    entries: ActivityEntry[]
    isComplete: boolean
    isError: boolean
    summary: string | null
    prompt: string | null
    strategyName: string | null
    onEditAndRerun?: (iterationId: string) => void
    onSuggestionClick?: (prompt: string, title?: string) => void
    suggestionsDisabled?: boolean
    defaultExpanded?: boolean
}
export function ActivityLogGroup({
    entries,
    isComplete,
    isError,
    summary,
    prompt,
    strategyName,
    onEditAndRerun,
    onSuggestionClick,
    suggestionsDisabled,
    defaultExpanded = false
}: ActivityLogGroupProps) {
    const [expanded, setExpanded] = useState(defaultExpanded)

    // Determine the display title for the collapsed state
    const title = strategyName || (prompt ? (prompt.length > 50 ? prompt.substring(0, 50) + '...' : prompt) : 'Generating Strategy...')

    // Determine current status message from the latest entry
    const statusMessage = useMemo(() => {
        if (summary) return summary

        // Find the latest active step, or the last done step if none active
        const activeStep = [...entries].reverse().find(e => e.status === 'active')
        if (activeStep) return activeStep.content

        const lastDone = [...entries].reverse().find(e => e.status === 'done' || e.type === 'auto-run')
        if (lastDone) return lastDone.content

        return 'Initializing...'
    }, [entries, summary])

    // Optional: Auto-expand if an error occurs while collapsed
    useEffect(() => {
        if (isError && !expanded) {
            setExpanded(true)
        }
    }, [isError, expanded])

    return (
        <div className="mb-3 ml-1 bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
            {/* Accordion Header (Summary) */}
            <button
                onClick={() => setExpanded(!expanded)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors ${isError ? 'bg-red-50 hover:bg-red-100' :
                    isComplete ? 'bg-emerald-50 hover:bg-emerald-100' :
                        'bg-slate-50 hover:bg-slate-100'
                    }`}
            >
                {/* Status Icon */}
                <div className="flex-shrink-0">
                    {isError ? (
                        <AlertCircle className="w-4 h-4 text-red-500" />
                    ) : isComplete ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : (
                        <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />
                    )}
                </div>

                {/* Title and Status Texts */}
                <div className="flex-1 min-w-0 flex flex-col justify-center">
                    <div className="flex items-center gap-2">
                        {!strategyName && <Sparkles className="w-3.5 h-3.5 text-primary-400" />}
                        {strategyName && <Terminal className="w-3.5 h-3.5 text-slate-400" />}
                        <span className="text-sm font-semibold text-slate-800 truncate">
                            {title}
                        </span>
                    </div>
                    <span className={`text-xs truncate ${isError ? 'text-red-600' : isComplete ? 'text-emerald-600' : 'text-slate-500'}`}>
                        {statusMessage}
                    </span>
                </div>

                {/* Expand/Collapse Chevron */}
                <div className="flex-shrink-0">
                    {expanded ? (
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                    ) : (
                        <ChevronRight className="w-4 h-4 text-slate-400" />
                    )}
                </div>
            </button>

            {/* Expanded Content: Individual Steps */}
            {expanded && (
                <div className="border-t border-slate-200 px-3 py-3 bg-white">
                    {entries.map((entry) => (
                        <ActivityLogEntry
                            key={entry.id}
                            entry={entry}
                            onEditAndRerun={onEditAndRerun}
                            onSuggestionClick={onSuggestionClick}
                            suggestionsDisabled={suggestionsDisabled}
                        />
                    ))}
                </div>
            )}
        </div>
    )
}
