import { useState, useCallback } from 'react'
import { useBacktest } from './hooks/useBacktest'
import { BacktestConfigBar } from './components/BacktestConfigBar'
import { ActivityLog } from './components/ActivityLog'
import { IterationPanel } from './components/IterationPanel'
import { ScriptEditorModal } from './components/ScriptEditorModal'
import { SessionPicker } from './components/SessionPicker'
import { MessageSquare, GitBranch } from 'lucide-react'

function App() {
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
    deleteIteration,
    selectIteration,
    archivedSessions,
    newSession,
    switchSession,
    deleteArchivedSession,
  } = useBacktest()

  const [mobileTab, setMobileTab] = useState<'activity' | 'iterations'>('activity')

  // Script editor modal state
  const [editorModal, setEditorModal] = useState<{
    iterationId: string
    code: string
    name: string
  } | null>(null)

  const handleSubmitPrompt = useCallback((prompt: string, model: string) => {
    // Find the latest completed iteration for previousScriptCode context
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
  }, [generateAndExecute, iterationHistory])

  const handleEditAndRerun = useCallback((iterationId: string) => {
    const iteration = iterationHistory.find(n => n.id === iterationId)
    if (!iteration || !iteration.scriptCode) return
    setEditorModal({
      iterationId: iteration.id,
      code: iteration.scriptCode,
      name: iteration.strategyName,
    })
  }, [iterationHistory])

  const handleSuggestionClick = useCallback((suggestionPrompt: string) => {
    // Find the latest completed iteration for previousScriptCode context
    const latestComplete = [...iterationHistory].reverse().find(n => n.status === 'complete')
    const metrics = latestComplete?.result ? {
      total_return: latestComplete.result.total_return,
      max_drawdown: latestComplete.result.max_drawdown,
      num_trades: latestComplete.result.num_trades,
      win_rate: latestComplete.result.win_rate,
      sharpe_ratio: latestComplete.result.sharpe_ratio,
      profit_factor: latestComplete.result.profit_factor,
    } : null
    generateAndExecute(suggestionPrompt, 'claude-haiku-4-5-20251001', latestComplete?.scriptCode, metrics)
  }, [generateAndExecute, iterationHistory])

  const configDisabled = phase === 'generating' || phase === 'executing'

  const latestComplete = [...iterationHistory].reverse().find(n => n.status === 'complete')

  const handleRerun = useCallback(() => {
    if (!latestComplete?.scriptCode) return
    editAndRerun(latestComplete.id, latestComplete.scriptCode)
  }, [latestComplete, editAndRerun])

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-4 py-3 lg:px-6 lg:py-4">
        <div className="flex items-center justify-between max-w-screen-2xl mx-auto">
          <div className="flex items-center gap-2 lg:gap-3 min-w-0">
            <div className="w-7 h-7 lg:w-8 lg:h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-white font-bold text-xs lg:text-sm">F</span>
            </div>
            <h1 className="text-base lg:text-xl font-semibold text-slate-800 truncate">
              Finovae Strategy Platform
            </h1>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0 ml-2">
            <SessionPicker
              archivedSessions={archivedSessions}
              hasCurrentIterations={iterationHistory.length > 0}
              isLoading={isLoading}
              onNewSession={() => { newSession(); setEditorModal(null) }}
              onSwitchSession={(id) => { switchSession(id); setEditorModal(null) }}
              onDeleteSession={deleteArchivedSession}
            />
            <span className="text-xs lg:text-sm text-slate-500">v0.3.0</span>
          </div>
        </div>
      </header>

      {/* Config Bar */}
      <BacktestConfigBar
        params={backtestParams}
        onChange={setBacktestParams}
        disabled={configDisabled}
        onRerun={handleRerun}
        canRerun={!!latestComplete}
      />

      {/* Mobile Tab Bar */}
      <div className="lg:hidden flex border-b border-slate-200 bg-white">
        <button
          onClick={() => setMobileTab('activity')}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-colors ${
            mobileTab === 'activity'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Activity
        </button>
        <button
          onClick={() => setMobileTab('iterations')}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-colors ${
            mobileTab === 'iterations'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500'
          }`}
        >
          <GitBranch className="w-4 h-4" />
          Iterations
          {iterationHistory.length > 0 && (
            <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-600 text-xs flex items-center justify-center font-semibold">
              {iterationHistory.length}
            </span>
          )}
        </button>
      </div>

      {/* Main Content */}
      <main className="flex flex-col lg:flex-row flex-1 lg:h-[calc(100vh-105px)] overflow-hidden">
        {/* Left Panel - Activity Log */}
        <div className={`${mobileTab === 'activity' ? 'flex' : 'hidden'} lg:flex w-full lg:w-1/2 lg:border-r border-slate-200 flex-col min-h-0`}>
          <ActivityLog
            entries={activityLog}
            onSubmitPrompt={handleSubmitPrompt}
            isLoading={isLoading}
            onEditAndRerun={handleEditAndRerun}
            onSuggestionClick={handleSuggestionClick}
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
          onRerun={editAndRerun}
          onClose={() => setEditorModal(null)}
        />
      )}
    </div>
  )
}

export default App
