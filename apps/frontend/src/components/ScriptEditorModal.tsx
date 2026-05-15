import { useState } from 'react'
import Editor from 'react-simple-code-editor'
import { highlight, languages } from 'prismjs'
import 'prismjs/components/prism-python'
import 'prismjs/themes/prism.css'
import { X, Play } from 'lucide-react'

interface ScriptEditorModalProps {
  iterationId: string
  initialCode: string
  strategyName: string
  onRerun: (iterationId: string, editedCode: string) => void
  onClose: () => void
}

export function ScriptEditorModal({
  iterationId,
  initialCode,
  strategyName,
  onRerun,
  onClose,
}: ScriptEditorModalProps) {
  const [code, setCode] = useState(initialCode)

  const handleRerun = () => {
    onRerun(iterationId, code)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-slate-800">Edit Strategy Script</h2>
            <p className="text-xs text-slate-500 mt-0.5 truncate">{strategyName}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Code Editor */}
        <div className="flex-1 overflow-y-auto border-b border-slate-200">
          <Editor
            value={code}
            onValueChange={setCode}
            highlight={c => highlight(c, languages.python, 'python')}
            padding={16}
            style={{
              fontFamily: '"Fira Code", "Fira Mono", monospace',
              fontSize: 13,
              lineHeight: 1.5,
              minHeight: '300px',
            }}
            className="code-editor"
          />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-5 py-4">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleRerun}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Play className="w-4 h-4" />
            Re-run Backtest
          </button>
        </div>
      </div>
    </div>
  )
}
