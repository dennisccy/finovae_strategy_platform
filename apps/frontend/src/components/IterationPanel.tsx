import { useEffect, useRef, useMemo } from 'react'
import { GitBranch, Loader2, AlertCircle, ChevronLeft } from 'lucide-react'
import type { IterationNode, WalkForwardConfig, AutoRunStatus } from '../hooks/useBacktest'
import { IterationCard } from './IterationCard'
import { IterationDetailView } from './IterationDetailView'
import { AutoSessionStatusStrip } from './AutoSessionStatusStrip'

interface IterationPanelProps {
  iterations: IterationNode[]
  selectedId: string | null
  onSelect: (id: string | null) => void
  onDelete: (id: string) => void
  onRerun: (id: string) => void
  onStartAutoRun: (id: string) => void
  isLoading: boolean
  onRunWalkForward?: (iterationId: string, config: WalkForwardConfig, onProgress?: (w: number, t: number) => void) => void
  /** True while the selected run's heavy detail is being lazy-fetched. */
  detailLoading?: boolean
  /** Set when the lazy per-iteration detail fetch failed. */
  detailError?: string | null
  /** Retry the lazy detail fetch for the currently selected run. */
  onRetryDetail?: () => void
  /** Backend automated-session status (null for a manual session). Rendered as
   *  the status strip pinned above the iteration tree. */
  autoRun?: AutoRunStatus | null
}

// =============================================================================
// Detail-pane status (loading / error / no-detail) — shown while the selected
// run's heavy payload is lazy-fetched on selection.
// =============================================================================

function DetailStatusPane({
  children,
  onBack,
}: {
  children: React.ReactNode
  onBack: () => void
}) {
  return (
    <div className="flex-1 flex flex-col bg-slate-50">
      <div className="p-4 border-b border-slate-200 bg-white">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          Back to history
        </button>
      </div>
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center max-w-sm">{children}</div>
      </div>
    </div>
  )
}

// =============================================================================
// Tree building
// =============================================================================

interface TreeNode {
  iteration: IterationNode
  children: TreeNode[]
  depth: number
}

function buildIterationTree(iterations: IterationNode[]): TreeNode[] {
  const byParent = new Map<string | null, IterationNode[]>()
  for (const iter of iterations) {
    const key = iter.parentId ?? null
    if (!byParent.has(key)) byParent.set(key, [])
    byParent.get(key)!.push(iter)
  }
  function makeNode(iter: IterationNode, depth: number): TreeNode {
    return {
      iteration: iter,
      children: (byParent.get(iter.id) ?? []).map(c => makeNode(c, depth + 1)),
      depth,
    }
  }
  return (byParent.get(null) ?? []).map(r => makeNode(r, 0))
}

// =============================================================================
// IterationTreeItem
// =============================================================================

interface IterationTreeItemProps {
  node: TreeNode
  latestId: string | null
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onRerun: (id: string) => void
  onStartAutoRun: (id: string) => void
}

function IterationTreeItem({ node, latestId, onSelect, onDelete, onRerun, onStartAutoRun }: IterationTreeItemProps) {
  return (
    <div className="relative">
      <IterationCard
        iteration={node.iteration}
        isLatest={node.iteration.id === latestId}
        onSelect={onSelect}
        onDelete={onDelete}
        onRerun={onRerun}
        onStartAutoRun={onStartAutoRun}
      />
      {node.children.length > 0 && (
        <div className="ml-4 mt-1.5 pl-3 border-l-2 border-slate-200 space-y-1.5">
          {node.children.map(child => (
            <IterationTreeItem
              key={child.iteration.id}
              node={child}
              latestId={latestId}
              onSelect={onSelect}
              onDelete={onDelete}
              onRerun={onRerun}
              onStartAutoRun={onStartAutoRun}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// IterationPanel
// =============================================================================

export function IterationPanel({ iterations, selectedId, onSelect, onDelete, onRerun, onStartAutoRun, onRunWalkForward, detailLoading, detailError, onRetryDetail, autoRun }: IterationPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const isUserScrolledUp = useRef(false)
  const lastScrollHeight = useRef(0)

  const sortedIterations = useMemo(
    () => [...iterations].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()),
    [iterations]
  )

  const tree = useMemo(() => buildIterationTree(sortedIterations), [sortedIterations])

  const latestId = sortedIterations[sortedIterations.length - 1]?.id ?? null

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

  // Detail view for selected iteration. The session list/open path is
  // lightweight, so the selected run's heavy detail (result/rating/trades/
  // scriptCode) is lazy-fetched on selection — render an explicit loading and
  // error state instead of a silent blank pane.
  if (selectedId) {
    const selected = sortedIterations.find(n => n.id === selectedId)
    if (selected) {
      if (selected.result) {
        // Use parent node's code as the "before" snapshot for diff view
        const previousIteration = selected.parentId
          ? sortedIterations.find(n => n.id === selected.parentId) ?? undefined
          : undefined

        return (
          <IterationDetailView
            iteration={selected}
            previousIteration={previousIteration}
            onBack={() => onSelect(null)}
            onRunWalkForward={onRunWalkForward}
          />
        )
      }

      if (detailLoading) {
        return (
          <DetailStatusPane onBack={() => onSelect(null)}>
            <Loader2 className="w-8 h-8 text-primary-500 animate-spin mx-auto" />
            <p className="mt-3 text-sm font-medium text-slate-600">Loading run detail…</p>
            <p className="mt-1 text-xs text-slate-400">
              Fetching this run's strategy, metrics, and trades.
            </p>
          </DetailStatusPane>
        )
      }

      if (detailError) {
        return (
          <DetailStatusPane onBack={() => onSelect(null)}>
            <AlertCircle className="w-8 h-8 text-red-500 mx-auto" />
            <p className="mt-3 text-sm font-medium text-slate-700">
              Couldn't load this run's detail
            </p>
            <p className="mt-1 text-xs text-slate-500 break-words">{detailError}</p>
            {onRetryDetail && (
              <button
                onClick={onRetryDetail}
                className="mt-4 px-3 py-1.5 text-xs font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
              >
                Retry
              </button>
            )}
          </DetailStatusPane>
        )
      }

      // Selected, not loading, no error, but no result on disk (e.g. an
      // errored/in-progress run). Don't crash the detail view — show a clear
      // message and keep the history list reachable via Back.
      return (
        <DetailStatusPane onBack={() => onSelect(null)}>
          <GitBranch className="w-8 h-8 text-slate-300 mx-auto" />
          <p className="mt-3 text-sm font-medium text-slate-600">
            No detailed results for this run
          </p>
          <p className="mt-1 text-xs text-slate-400">
            This run has no stored metrics or trades to display.
          </p>
        </DetailStatusPane>
      )
    }
  }

  // Empty state — still show the auto-session strip if a run just started but
  // hasn't produced its first iteration yet (so "Running" is visible).
  if (sortedIterations.length === 0) {
    return (
      <div className="flex-1 flex flex-col bg-slate-50 p-4 lg:p-6">
        {autoRun && <AutoSessionStatusStrip autoRun={autoRun} />}
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="w-12 h-12 lg:w-16 lg:h-16 bg-slate-200 rounded-full flex items-center justify-center mx-auto">
              <GitBranch className="w-6 h-6 lg:w-8 lg:h-8 text-slate-400" />
            </div>
            <h3 className="mt-3 lg:mt-4 text-base lg:text-lg font-semibold text-slate-600">
              {autoRun ? 'Waiting for the first iteration…' : 'No Iterations Yet'}
            </h3>
            <p className="mt-2 text-xs lg:text-sm text-slate-500 max-w-xs">
              {autoRun
                ? 'The automated session is generating and backtesting its first strategy.'
                : 'Your strategy iterations will appear here. Describe a strategy to get started.'}
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto bg-slate-50 p-4 lg:p-6">
      {autoRun && <AutoSessionStatusStrip autoRun={autoRun} />}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-700">
          Iterations ({sortedIterations.length})
        </h2>
      </div>
      <div className="space-y-2">
        {tree.map(root => (
          <IterationTreeItem
            key={root.iteration.id}
            node={root}
            latestId={latestId}
            onSelect={onSelect}
            onDelete={onDelete}
            onRerun={onRerun}
            onStartAutoRun={onStartAutoRun}
          />
        ))}
      </div>
    </div>
  )
}
