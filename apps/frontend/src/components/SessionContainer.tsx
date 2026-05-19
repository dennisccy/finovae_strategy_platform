import { useState, useCallback, useEffect, useRef } from 'react'
import { Loader2, CheckCircle2, StopCircle } from 'lucide-react'
import { useBacktest, type LiveSessionStatus, type IterationNode, type AutoRunStatus } from '../hooks/useBacktest'
import { useDirectionsCache, type RunOneCard } from '../hooks/useDirectionsCache'
import { fetchCachedDirection } from '../lib/directionsApi'
import { BacktestConfigBar } from './BacktestConfigBar'
import { ActivityLog } from './ActivityLog'
import { IterationPanel } from './IterationPanel'
import { ScriptEditorModal } from './ScriptEditorModal'
import type { DirectionCacheSummary } from '../lib/directionsApi'
import type { ModelOption } from '../lib/modelsApi'
import type { StrategyCard } from '../data/strategyPrompts'

interface SessionContainerProps {
  sessionId: string
  sessionName: string
  isActive: boolean
  mobileTab: 'activity' | 'iterations'
  lastUsedModel: string
  availableModels: ModelOption[]
  onLastUsedModelChange: (model: string) => void
  onStatusChange: (status: LiveSessionStatus) => void
  onNameChange: (name: string) => void
}

/**
 * Live status strip for a headless (server-driven) auto-session. Advances
 * running → terminal without a manual page reload (J-08) and shows the
 * terminal stop reason (J-09). Hidden for manual sessions (autoRun null).
 */
function AutoRunBar({ autoRun }: { autoRun: AutoRunStatus }) {
  const { status, stopReason, currentIteration, maxIterations } = autoRun
  const active = status === 'running' || status === 'queued'

  let icon = <Loader2 className="w-3.5 h-3.5 animate-spin text-primary-600" />
  let text = `Automated run · iteration ${currentIteration}/${maxIterations}`
  let tone = 'bg-primary-50 border-primary-200 text-primary-700'

  if (!active) {
    if (status === 'stopped') {
      icon = <StopCircle className="w-3.5 h-3.5 text-red-500" />
      text = 'Automated run stopped'
      tone = 'bg-red-50 border-red-200 text-red-700'
    } else {
      icon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
      const reason =
        stopReason === 'criteria-met'
          ? 'robust targets met'
          : stopReason === 'budget-exhausted'
          ? 'budget reached'
          : 'finished'
      text = `Automated run complete · ${reason} · ${currentIteration}/${maxIterations} iterations`
      tone = 'bg-emerald-50 border-emerald-200 text-emerald-700'
    }
  }

  return (
    <div
      className={`flex items-center gap-2 px-4 py-1.5 border-b text-xs font-medium ${tone}`}
      role="status"
      aria-live="polite"
    >
      {icon}
      <span className="truncate">{text}</span>
      {status === 'queued' && <span className="text-slate-400">(queued)</span>}
    </div>
  )
}

export function SessionContainer({
  sessionId,
  sessionName: _sessionName,
  isActive,
  mobileTab,
  lastUsedModel,
  availableModels,
  onLastUsedModelChange,
  onStatusChange,
  onNameChange,
}: SessionContainerProps) {
  const {
    phase,
    isLoading,
    backtestParams,
    setBacktestParams,
    activityLog,
    selectedIterationId,
    iterationHistory,
    detailLoading,
    detailError,
    retryDetailLoad,
    generateAndExecute,
    editAndRerun,
    cancelOperation,
    deleteIteration,
    selectIteration,
    loadCachedIteration,
    loadCachedAsStartingPoint,
    isAutoRunning,
    autoRunProgress,
    startAutoSession,
    stopAutoSession,
    runWalkForward,
    sessionStatus,
    workerCount,
    autoRun,
  } = useBacktest(sessionId, isActive)

  // Directions cache
  const {
    cacheResult,
    isRunningAll,
    runAllProgress,
    concurrency,
    setConcurrency,
    runAllDirections,
    stopRunAll,
  } = useDirectionsCache(backtestParams)

  const [autoRunCount, setAutoRunCount] = useState(1)
  const [pendingCachedNode, setPendingCachedNode] = useState<IterationNode | null>(null)
  const [pendingCardTitle, setPendingCardTitle] = useState<string>('')
  const [editorModal, setEditorModal] = useState<{
    iterationId: string
    code: string
    name: string
  } | null>(null)

  // Propagate status changes to App.tsx
  // Use a ref to track the last reported status to avoid infinite loops
  // since sessionStatus is a new object reference on many renders
  const lastReportedStatusRef = useRef<string>('')
  
  useEffect(() => {
    const statusKey = `${sessionStatus.isLoading}-${sessionStatus.isAutoRunning}-${sessionStatus.iterationCount}-${sessionStatus.bestReturn}-${sessionStatus.hasError}`
    if (lastReportedStatusRef.current !== statusKey) {
      lastReportedStatusRef.current = statusKey
      onStatusChange(sessionStatus)
    }
  }, [sessionStatus, onStatusChange])

  // Propagate name changes when first complete iteration arrives
  const lastReportedNameRef = useRef<string>('')
  useEffect(() => {
    const firstComplete = iterationHistory.find(n => n.status === 'complete' && n.strategyName)
    if (firstComplete?.strategyName && lastReportedNameRef.current !== firstComplete.strategyName) {
      lastReportedNameRef.current = firstComplete.strategyName
      onNameChange(firstComplete.strategyName)
    }
  }, [iterationHistory, onNameChange])

  const handleSubmitPrompt = useCallback((prompt: string, model: string) => {
    onLastUsedModelChange(model)
    const latestComplete = [...iterationHistory].reverse().find(n => n.status === 'complete')
    const metrics = latestComplete?.result ? {
      total_return: latestComplete.result.total_return,
      max_drawdown: latestComplete.result.max_drawdown,
      num_trades: latestComplete.result.num_trades,
      win_rate: latestComplete.result.win_rate,
      sharpe_ratio: latestComplete.result.sharpe_ratio,
      profit_factor: latestComplete.result.profit_factor,
    } : null
    generateAndExecute(prompt, model, latestComplete?.scriptCode, metrics)
  }, [generateAndExecute, iterationHistory, onLastUsedModelChange])

  const handleEditAndRerun = useCallback((iterationId: string) => {
    const iteration = iterationHistory.find(n => n.id === iterationId)
    if (!iteration || !iteration.scriptCode) return
    setEditorModal({
      iterationId: iteration.id,
      code: iteration.scriptCode,
      name: iteration.strategyName,
    })
  }, [iterationHistory])

  const handleSuggestionClick = useCallback((suggestionPrompt: string, suggestionTitle?: string) => {
    const latestComplete = [...iterationHistory].reverse().find(n => n.status === 'complete')
    const metrics = latestComplete?.result ? {
      total_return: latestComplete.result.total_return,
      max_drawdown: latestComplete.result.max_drawdown,
      num_trades: latestComplete.result.num_trades,
      win_rate: latestComplete.result.win_rate,
      sharpe_ratio: latestComplete.result.sharpe_ratio,
      profit_factor: latestComplete.result.profit_factor,
    } : null
    generateAndExecute(suggestionPrompt, lastUsedModel, latestComplete?.scriptCode, metrics, undefined, undefined, false, suggestionTitle)
  }, [generateAndExecute, iterationHistory, lastUsedModel])

  const handleCachedDirectionClick = useCallback(async (card: StrategyCard, _summary: DirectionCacheSummary) => {
    const node = await fetchCachedDirection(backtestParams, card.id)
    if (node) {
      setPendingCachedNode(node)
      setPendingCardTitle(card.title)
    }
  }, [backtestParams])

  const handleRunAll = useCallback((cards: StrategyCard[]) => {
    const runOneCard: RunOneCard = async (card, signal) => {
      const directionIndex = parseInt(card.id.split('-')[1] ?? '0', 10)
      return await generateAndExecute(
        card.prompt, lastUsedModel, undefined, null, undefined, undefined, true, card.title, signal,
        card.id, directionIndex, card.prompt,
      )
    }
    runAllDirections(cards, runOneCard)
  }, [generateAndExecute, lastUsedModel, runAllDirections])

  const configDisabled = phase === 'generating' || phase === 'executing'

  // Rerun from any card — re-executes same code as a child of that iteration
  const handleRerunFromCard = useCallback((iterationId: string) => {
    const iteration = iterationHistory.find(n => n.id === iterationId)
    if (!iteration || !iteration.scriptCode) return
    editAndRerun(iterationId, iteration.scriptCode, lastUsedModel)
  }, [iterationHistory, editAndRerun, lastUsedModel])

  // Auto run from any card — starts a SERVER-DRIVEN auto-session pinned to
  // that completed iteration's config (no in-browser loop). The new backend
  // session appears in the session list via App.tsx's discovery poll.
  const handleStartAutoRunFromCard = useCallback((iterationId: string) => {
    startAutoSession(iterationId, autoRunCount, lastUsedModel)
  }, [autoRunCount, lastUsedModel, startAutoSession])

  const canAutoRun = iterationHistory.some(
    n => n.status === 'complete' && (n.insights?.suggestions?.length ?? 0) > 0
  ) && !isAutoRunning && !isLoading

  return (
    <div style={{ display: isActive ? 'contents' : 'none' }}>
      {/* Config Bar */}
      <BacktestConfigBar
        params={backtestParams}
        onChange={setBacktestParams}
        disabled={configDisabled}
        isAutoRunning={isAutoRunning}
        autoRunProgress={autoRunProgress}
        canAutoRun={canAutoRun}
        autoRunCount={autoRunCount}
        onAutoRunCountChange={setAutoRunCount}
        onStartAutoRun={() => {
          const baseline = [...iterationHistory].reverse()
            .find(n => n.status === 'complete' && (n.insights?.suggestions?.length ?? 0) > 0)
          if (baseline) startAutoSession(baseline.id, autoRunCount, lastUsedModel)
        }}
        onStopAutoRun={stopAutoSession}
        workerCount={workerCount}
      />

      {/* Headless auto-session live status (J-08/J-09) */}
      {autoRun && <AutoRunBar autoRun={autoRun} />}

      {/* Main Content */}
      <main className="flex flex-col lg:flex-row flex-1 lg:h-[calc(100vh-105px)] overflow-hidden">
        {/* Left Panel - Activity Log */}
        <div className={`${mobileTab === 'activity' ? 'flex' : 'hidden'} lg:flex w-full lg:w-1/2 lg:border-r border-slate-200 flex-col overflow-hidden min-h-0`}>
          <ActivityLog
            entries={activityLog}
            availableModels={availableModels}
            onSubmitPrompt={handleSubmitPrompt}
            currentSymbol={backtestParams.symbol}
            currentTimeframe={backtestParams.timeframe}
            isLoading={isLoading}
            onEditAndRerun={handleEditAndRerun}
            onSuggestionClick={handleSuggestionClick}
            onCancel={cancelOperation}
            allowShort={backtestParams.allow_short ?? false}
            cacheResult={cacheResult}
            isRunningAll={isRunningAll}
            runAllProgress={runAllProgress}
            concurrency={concurrency}
            onConcurrencyChange={setConcurrency}
            onRunAll={handleRunAll}
            onStopRunAll={stopRunAll}
            onCachedDirectionClick={handleCachedDirectionClick}
          />
        </div>

        {/* Right Panel - Iteration Panel */}
        <div className={`${mobileTab === 'iterations' ? 'flex' : 'hidden'} lg:flex w-full lg:w-1/2 flex-col overflow-hidden min-h-0`}>
          <IterationPanel
            iterations={iterationHistory}
            selectedId={selectedIterationId}
            onSelect={selectIteration}
            onDelete={deleteIteration}
            onRerun={handleRerunFromCard}
            onStartAutoRun={handleStartAutoRunFromCard}
            isLoading={isLoading}
            onRunWalkForward={runWalkForward}
            detailLoading={detailLoading}
            detailError={detailError}
            onRetryDetail={retryDetailLoad}
            bestIterationId={autoRun?.bestIterationId ?? null}
          />
        </div>
      </main>

      {/* Script Editor Modal */}
      {editorModal && (
        <ScriptEditorModal
          iterationId={editorModal.iterationId}
          initialCode={editorModal.code}
          strategyName={editorModal.name}
          onRerun={(iterationId, code) => editAndRerun(iterationId, code, lastUsedModel)}
          onClose={() => setEditorModal(null)}
        />
      )}

      {/* Cached Direction Confirmation Modal */}
      {pendingCachedNode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl p-6 w-96 shadow-xl">
            <h3 className="text-base font-semibold text-slate-800 mb-1">{pendingCardTitle}</h3>
            <p className="text-sm text-slate-500 mb-1">{pendingCachedNode.strategyName}</p>
            <p className="text-sm text-slate-600 mb-4">
              Start iterating from this direction? You'll see its suggestions and can type follow-up prompts.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => { loadCachedAsStartingPoint(pendingCachedNode!); setPendingCachedNode(null) }}
                className="flex-1 px-3 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700"
              >
                Start iteration
              </button>
              <button
                onClick={() => { loadCachedIteration(pendingCachedNode!); setPendingCachedNode(null) }}
                className="flex-1 px-3 py-2 border border-slate-200 text-sm text-slate-600 rounded-lg hover:bg-slate-50"
              >
                Just view
              </button>
              <button
                onClick={() => setPendingCachedNode(null)}
                className="px-3 py-2 text-sm text-slate-400 hover:text-slate-600"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
