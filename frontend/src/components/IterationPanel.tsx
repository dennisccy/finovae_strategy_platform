import { useEffect, useRef, useMemo } from 'react'
import { GitBranch } from 'lucide-react'
import type { IterationNode, WalkForwardConfig } from '../hooks/useBacktest'
import { IterationCard } from './IterationCard'
import { IterationDetailView } from './IterationDetailView'

interface IterationPanelProps {
  iterations: IterationNode[]
  selectedId: string | null
  onSelect: (id: string | null) => void
  onDelete: (id: string) => void
  onRerun: (id: string) => void
  onStartAutoRun: (id: string) => void
  isLoading: boolean
  onRunWalkForward?: (iterationId: string, config: WalkForwardConfig, onProgress?: (w: number, t: number) => void) => void
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

export function IterationPanel({ iterations, selectedId, onSelect, onDelete, onRerun, onStartAutoRun, onRunWalkForward }: IterationPanelProps) {
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

  // Detail view for selected iteration
  if (selectedId) {
    const selected = sortedIterations.find(n => n.id === selectedId)
    if (selected && selected.result) {
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
  }

  // Empty state
  if (sortedIterations.length === 0) {
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

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto bg-slate-50 p-4 lg:p-6">
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
