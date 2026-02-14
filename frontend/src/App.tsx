import { useState } from 'react'
import { ChatPanel } from './components/ChatPanel'
import { ScriptReviewPanel } from './components/ScriptReviewPanel'
import { ResultsPanel } from './components/ResultsPanel'
import { useBacktest } from './hooks/useBacktest'
import { BarChart3, MessageSquare, Code } from 'lucide-react'

function App() {
  const {
    phase,
    isLoading,
    error,
    result,
    rating,
    strategySpec,
    runHistory,
    generatedScript,
    scriptCode,
    setScriptCode,
    generateStrategy,
    executeBacktest,
    resetToIdle,
    backToReview,
  } = useBacktest()

  const [mobileTab, setMobileTab] = useState<'strategy' | 'results'>('strategy')

  const showChat = phase === 'idle' || phase === 'generating'
  const showReview = phase === 'review' || phase === 'executing'
  const showResults = phase === 'results'

  // Left panel content based on phase
  const renderLeftPanel = () => {
    if (showChat) {
      return (
        <ChatPanel
          onGenerate={async (nl, model) => {
            await generateStrategy(nl, model)
            setMobileTab('results')
          }}
          isLoading={isLoading}
          runHistory={runHistory}
        />
      )
    }

    if (showReview && generatedScript && scriptCode !== null) {
      return (
        <ScriptReviewPanel
          script={generatedScript}
          scriptCode={scriptCode}
          onScriptCodeChange={setScriptCode}
          onExecute={async (params) => {
            await executeBacktest(params)
            setMobileTab('results')
          }}
          onRegenerate={resetToIdle}
          isLoading={isLoading}
          error={error}
        />
      )
    }

    if (showResults) {
      return (
        <ChatPanel
          onGenerate={async (nl, model) => {
            await generateStrategy(nl, model)
            setMobileTab('results')
          }}
          isLoading={isLoading}
          runHistory={runHistory}
        />
      )
    }

    return null
  }

  // Mobile tab label for left panel
  const leftTabLabel = showReview ? 'Script' : 'Strategy'
  const LeftTabIcon = showReview ? Code : MessageSquare

  return (
    <div className="min-h-screen bg-slate-50">
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
          <span className="text-xs lg:text-sm text-slate-500 flex-shrink-0 ml-2">v0.2.0</span>
        </div>
      </header>

      {/* Mobile Tab Bar */}
      <div className="lg:hidden flex border-b border-slate-200 bg-white">
        <button
          onClick={() => setMobileTab('strategy')}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-colors ${
            mobileTab === 'strategy'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500'
          }`}
        >
          <LeftTabIcon className="w-4 h-4" />
          {leftTabLabel}
        </button>
        <button
          onClick={() => setMobileTab('results')}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-colors ${
            mobileTab === 'results'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-slate-500'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Results
          {result && (
            <span className={`w-2 h-2 rounded-full ${result.total_return >= 0 ? 'bg-emerald-500' : 'bg-red-500'}`} />
          )}
        </button>
      </div>

      {/* Main Content */}
      <main className="flex flex-col lg:flex-row lg:h-[calc(100vh-73px)]">
        {/* Left Panel */}
        <div className={`${mobileTab === 'strategy' ? 'flex' : 'hidden'} lg:flex w-full lg:w-1/2 lg:border-r border-slate-200 flex-col min-h-[calc(100vh-113px)] lg:min-h-0`}>
          {renderLeftPanel()}
        </div>

        {/* Right Panel - Results */}
        <div className={`${mobileTab === 'results' ? 'flex' : 'hidden'} lg:flex w-full lg:w-1/2 flex-col overflow-hidden min-h-[calc(100vh-113px)] lg:min-h-0`}>
          <ResultsPanel
            result={result}
            rating={rating}
            strategySpec={strategySpec}
            generatedScript={generatedScript}
            scriptCode={scriptCode}
            isLoading={isLoading && (phase === 'executing' || phase === 'generating')}
            error={showChat ? error : null}
            onBackToReview={showResults && generatedScript ? backToReview : undefined}
          />
        </div>
      </main>
    </div>
  )
}

export default App
