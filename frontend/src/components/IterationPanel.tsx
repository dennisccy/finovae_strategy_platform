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
  // Detail view for selected iteration
  if (selectedId) {
    const selected = iterations.find(n => n.id === selectedId)
    if (selected && selected.result) {
      return (
        <IterationDetailView
          iteration={selected}
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

  // Iteration list (newest first)
  return (
    <div className="flex-1 overflow-y-auto bg-slate-50 p-4 lg:p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-700">
          Iterations ({iterations.length})
        </h2>
      </div>
      <div className="space-y-3">
        {[...iterations].reverse().map((iteration) => (
          <IterationCard
            key={iteration.id}
            iteration={iteration}
            onSelect={() => onSelect(iteration.id)}
            onDelete={() => onDelete(iteration.id)}
          />
        ))}
      </div>
    </div>
  )
}
