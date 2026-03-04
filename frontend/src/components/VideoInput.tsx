import { useState, useCallback } from 'react'
import { Youtube, Clipboard, Loader2 } from 'lucide-react'

const YOUTUBE_URL_RE = /(?:youtube\.com\/watch\?.*v=|youtu\.be\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/

interface VideoInputProps {
  videoUrl: string
  onVideoUrlChange: (url: string) => void
  onExtract: (url: string, model: string) => void
  isProcessing: boolean
  disabled?: boolean
  model: string
  onModelChange: (model: string) => void
}

function extractVideoId(url: string): string | null {
  const match = YOUTUBE_URL_RE.exec(url)
  return match ? match[1] : null
}

const MODEL_OPTIONS = [
  { value: 'claude-sonnet-4-6', label: 'Sonnet 4.6' },
  { value: 'claude-haiku-4-5-20251001', label: 'Haiku 4.5' },
]

export function VideoInput({
  videoUrl,
  onVideoUrlChange,
  onExtract,
  isProcessing,
  disabled = false,
  model,
  onModelChange,
}: VideoInputProps) {
  const [pasteError, setPasteError] = useState<string | null>(null)

  const videoId = extractVideoId(videoUrl)
  const isValidUrl = videoId !== null

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText()
      onVideoUrlChange(text.trim())
      setPasteError(null)
    } catch {
      setPasteError('Could not read clipboard')
      setTimeout(() => setPasteError(null), 2000)
    }
  }, [onVideoUrlChange])

  const handleExtract = useCallback(() => {
    if (isValidUrl) {
      onExtract(videoUrl, model)
    }
  }, [videoUrl, model, isValidUrl, onExtract])

  return (
    <div className="space-y-3">
      {/* URL Input */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Youtube className="h-4 w-4 text-red-500" />
          </div>
          <input
            type="text"
            value={videoUrl}
            onChange={(e) => onVideoUrlChange(e.target.value)}
            placeholder="Paste YouTube video URL..."
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white"
            disabled={disabled || isProcessing}
          />
        </div>
        <button
          onClick={handlePaste}
          disabled={disabled || isProcessing}
          className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
          title="Paste from clipboard"
        >
          <Clipboard className="h-4 w-4" />
        </button>
      </div>

      {pasteError && (
        <p className="text-xs text-red-500">{pasteError}</p>
      )}

      {/* Video Thumbnail Preview */}
      {videoId && (
        <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
          <img
            src={`https://img.youtube.com/vi/${videoId}/mqdefault.jpg`}
            alt="Video thumbnail"
            className="w-32 h-auto rounded flex-shrink-0"
          />
          <div className="min-w-0 flex-1">
            <p className="text-xs text-slate-500 truncate">
              Video ID: {videoId}
            </p>
          </div>
        </div>
      )}

      {/* Model + Extract Button */}
      <div className="flex items-center gap-2">
        <select
          value={model}
          onChange={(e) => onModelChange(e.target.value)}
          disabled={disabled || isProcessing}
          className="text-sm border border-slate-300 rounded-lg px-2 py-2 bg-white focus:ring-2 focus:ring-primary-500"
        >
          {MODEL_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        <button
          onClick={handleExtract}
          disabled={!isValidUrl || isProcessing || disabled}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isProcessing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Extracting Strategy...
            </>
          ) : (
            'Extract Strategy'
          )}
        </button>
      </div>
    </div>
  )
}
