import { useEffect, useRef } from 'react'
import { GitBranch } from 'lucide-react'
import type { IterationNode } from '../hooks/useBacktest'
import { IterationCard } from './IterationCard'
import { IterationDetailView } from './IterationDetailView'

interface IterationPanelProps {
  iterations: IterationNode[]
  selectedId: string | null
  onSelect: (id: string | null) => void
  onDelete: (id: string) => void
  isLoading: boolean
}

export function IterationPanel({ iterations, selectedId, onSelect, onDelete }: IterationPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const isUserScrolledUp = useRef(false)
  const lastScrollHeight = useRef(0)

  // Auto-scroll to bottom when iterations change
  useEffect(() => {
    if (scrollRef.current && !selectedId && !isUserScrolledUp.current) {
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
  }, [iterations, selectedId])

  // Detect user scroll
  useEffect(() => {
    const element = scrollRef.current
    if (!element) return

    const handleScroll = () => {
      const isAtBottom = element.scrollHeight - element.scrollTop - element.clientHeight < 50
      isUserScrolledUp.current = !isAtBottom

      if (isAtBottom) {
        setTimeout(() => {
          isUserScrolledUp.current = false
        }, 2000)
      }
    }

    element.addEventListener('scroll', handleScroll)
    return () => element.removeEventListener('scroll', handleScroll)
  }, [])

  // Detail view for selected iteration
  if (selectedId) {
    const selected = iterations.find(n => n.id === selectedId)
    if (selected && selected.result) {
      // Find the most recent complete iteration before the selected one
      const selectedIdx = iterations.findIndex(n => n.id === selectedId)
      const prevComplete = iterations.slice(0, selectedIdx).filter(n => n.status === 'complete')
      const previousIteration = prevComplete.length > 0 ? prevComplete[prevComplete.length - 1] : undefined

      return (
        <IterationDetailView
          iteration={selected}
          previousIteration={previousIteration}
          onBack={() => onSelect(null)}
        />
      )
    }
  }

  // Empty state
  if (iterations.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-50 p-4">
        <div className="text-center">
          <div className="w-12 h-12 lg:w-16 lg:h-16 bg-slate-200 rounded-full flex items-center justify-center mx-auto">
            <GitBranch className="w-6 h-6 lg:w-8 lg:h-8 text-slate-400" />
          </div>
          <h3 className="mt-3 lg:mt-4 text-base lg:text-lg font-semibold text-slate-600">
            No Iterations Yet
          </h3>
          <p className="mt-2 text-xs lg:text-sm text-slate-500 max-w-xs">
            Your strategy iterations will appear here. Describe a strategy to get started.
          </p>
        </div>
      </div>
    )
  }

  // Iteration list (oldest first, latest at bottom)
  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto bg-slate-50 p-4 lg:p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-700">
          Iterations ({iterations.length})
        </h2>
      </div>
      <div className="space-y-2">
        {iterations.map((iteration, index) => (
          <IterationCard
            key={iteration.id}
            iteration={iteration}
            onSelect={() => onSelect(iteration.id)}
            onDelete={() => onDelete(iteration.id)}
            isLatest={index === iterations.length - 1}
          />
        ))}
      </div>
    </div>
  )
}
