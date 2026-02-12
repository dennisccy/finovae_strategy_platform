import { ChatPanel } from './components/ChatPanel'
import { ResultsPanel } from './components/ResultsPanel'
import { useBacktest } from './hooks/useBacktest'

function App() {
  const {
    isLoading,
    error,
    result,
    strategySpec,
    runHistory,
    runBacktest,
  } = useBacktest()

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="flex items-center justify-between max-w-screen-2xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">F</span>
            </div>
            <h1 className="text-xl font-semibold text-slate-800">
              Finovae Strategy Platform
            </h1>
          </div>
          <span className="text-sm text-slate-500">v0.1.0 MVP</span>
        </div>
      </header>

      {/* Main Content - Split View */}
      <main className="flex h-[calc(100vh-73px)]">
        {/* Left Panel - Chat */}
        <div className="w-1/2 border-r border-slate-200 flex flex-col">
          <ChatPanel
            onSubmit={runBacktest}
            isLoading={isLoading}
            runHistory={runHistory}
          />
        </div>

        {/* Right Panel - Results */}
        <div className="w-1/2 flex flex-col overflow-hidden">
          <ResultsPanel
            result={result}
            strategySpec={strategySpec}
            isLoading={isLoading}
            error={error}
          />
        </div>
      </main>
    </div>
  )
}

export default App
