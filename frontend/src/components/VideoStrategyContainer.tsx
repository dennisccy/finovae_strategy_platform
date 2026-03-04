import { useState, useCallback, useEffect } from 'react'
import { useBacktest, type LiveSessionStatus } from '../hooks/useBacktest'
import { useVideoStrategy } from '../hooks/useVideoStrategy'
import { VideoInput } from './VideoInput'
import { ExtractedStrategyCard } from './ExtractedStrategyCard'
import { BacktestConfigBar } from './BacktestConfigBar'
import { ActivityLog } from './ActivityLog'
import { IterationPanel } from './IterationPanel'
import { ScriptEditorModal } from './ScriptEditorModal'

interface VideoStrategyContainerProps {
  sessionId: string
  sessionName: string
  isActive: boolean
  mobileTab: 'activity' | 'iterations'
  lastUsedModel: string
  onLastUsedModelChange: (model: string) => void
  onStatusChange: (status: LiveSessionStatus) => void
  onNameChange: (name: string) => void
}

export function VideoStrategyContainer({
  sessionId,
  sessionName: _sessionName,
  isActive,
  mobileTab,
  lastUsedModel,
  onLastUsedModelChange,
  onStatusChange,
  onNameChange,
}: VideoStrategyContainerProps) {
  // Backtest state (reused from standard flow)
  const {
    phase,
    isLoading,
    backtestParams,
    setBacktestParams,
    activityLog,
    selectedIterationId,
    iterationHistory,
    generateAndExecute,
    editAndRerun,
    cancelOperation,
    deleteIteration,
    selectIteration,
    isAutoRunning,
    autoRunProgress,
    startAutoRun,
    stopAutoRun,
    sessionStatus,
  } = useBacktest(sessionId)

  // Video-specific state
  const {
    videoUrl,
    setVideoUrl,
    isProcessingVideo,
    videoResult,
    videoError,
    processVideo,
    resetVideo: _resetVideo,
  } = useVideoStrategy()

  const [autoRunCount, setAutoRunCount] = useState(10)
  const [extractionModel, setExtractionModel] = useState(lastUsedModel)
  const [editorModal, setEditorModal] = useState<{
    iterationId: string
    code: string
    name: string
  } | null>(null)

  // Propagate status changes to App.tsx
  useEffect(() => {
    onStatusChange(sessionStatus)
  }, [sessionStatus, onStatusChange])

  // Propagate name changes
  useEffect(() => {
    const firstComplete = iterationHistory.find(n => n.status === 'complete' && n.strategyName)
    if (firstComplete?.strategyName) {
      onNameChange(firstComplete.strategyName)
    }
  }, [iterationHistory, onNameChange])

  // Handle video extraction
  const handleExtract = useCallback((url: string, model: string) => {
    setExtractionModel(model)
    processVideo(
      url,
      model,
      backtestParams.symbol,
      backtestParams.timeframes[0],
    )
  }, [processVideo, backtestParams.symbol, backtestParams.timeframes])

  // Handle running backtest from extracted strategy
  const handleRunBacktest = useCallback((prompt: string) => {
    onLastUsedModelChange(lastUsedModel)
    generateAndExecute(
      prompt,
      lastUsedModel,
      undefined, // no previous script
      null,      // no previous metrics
      undefined,
      undefined,
      false,
      videoResult?.strategy_name,
    )
  }, [generateAndExecute, lastUsedModel, onLastUsedModelChange, videoResult])

  // Handle suggestion click (same as SessionContainer)
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

  // Handle prompt submission (refinement iterations)
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

  const configDisabled = phase === 'generating' || phase === 'executing'
  const latestComplete = [...iterationHistory].reverse().find(n => n.status === 'complete')
  const canAutoRun = !!latestComplete?.insights?.suggestions?.length && !isAutoRunning && !isLoading

  const handleRerun = useCallback(() => {
    if (!latestComplete?.scriptCode) return
    editAndRerun(latestComplete.id, latestComplete.scriptCode, lastUsedModel)
  }, [latestComplete, editAndRerun, lastUsedModel])

  const hasIterations = iterationHistory.length > 0

  return (
    <div style={{ display: isActive ? 'contents' : 'none' }}>
      {/* Config Bar */}
      <BacktestConfigBar
        params={backtestParams}
        onChange={setBacktestParams}
        disabled={configDisabled}
        onRerun={handleRerun}
        canRerun={!!latestComplete}
        isAutoRunning={isAutoRunning}
        autoRunProgress={autoRunProgress}
        canAutoRun={canAutoRun}
        autoRunCount={autoRunCount}
        onAutoRunCountChange={setAutoRunCount}
        onStartAutoRun={() => startAutoRun(autoRunCount, lastUsedModel)}
        onStopAutoRun={stopAutoRun}
      />

      {/* Main Content */}
      <main className="flex flex-col lg:flex-row flex-1 lg:h-[calc(100vh-105px)] overflow-hidden">
        {/* Left Panel */}
        <div className={`${mobileTab === 'activity' ? 'flex' : 'hidden'} lg:flex w-full lg:w-1/2 lg:border-r border-slate-200 flex-col overflow-hidden min-h-0`}>
          {/* Video Input Section (shown when no iterations yet) */}
          {!hasIterations && (
            <div className="p-4 border-b border-slate-200 bg-white space-y-3">
              <h2 className="text-sm font-semibold text-slate-700">Video Strategy Extraction</h2>
              <VideoInput
                videoUrl={videoUrl}
                onVideoUrlChange={setVideoUrl}
                onExtract={handleExtract}
                isProcessing={isProcessingVideo}
                disabled={isLoading}
                model={extractionModel}
                onModelChange={setExtractionModel}
              />
              {videoError && (
                <div className="p-2 bg-red-50 text-red-700 text-sm rounded-lg border border-red-200">
                  {videoError}
                </div>
              )}
              {videoResult && (
                <ExtractedStrategyCard
                  result={videoResult}
                  onRunBacktest={handleRunBacktest}
                  disabled={isLoading}
                />
              )}
            </div>
          )}

          {/* Activity Log */}
          <ActivityLog
            entries={activityLog}
            onSubmitPrompt={handleSubmitPrompt}
            currentSymbol={backtestParams.symbol}
            currentTimeframe={backtestParams.timeframes[0] ?? '4h'}
            isLoading={isLoading}
            onEditAndRerun={handleEditAndRerun}
            onSuggestionClick={handleSuggestionClick}
            onCancel={cancelOperation}
            allowShort={backtestParams.allow_short ?? false}
          />
        </div>

        {/* Right Panel - Iteration Panel */}
        <div className={`${mobileTab === 'iterations' ? 'flex' : 'hidden'} lg:flex w-full lg:w-1/2 flex-col overflow-hidden min-h-0`}>
          <IterationPanel
            iterations={iterationHistory}
            selectedId={selectedIterationId}
            onSelect={selectIteration}
            onDelete={deleteIteration}
            isLoading={isLoading}
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
    </div>
  )
}
