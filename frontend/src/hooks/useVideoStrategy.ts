import { useState, useCallback } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export interface VideoResult {
  video_id: string
  title: string
  channel: string
  strategy_name: string
  strategy_description: string
  natural_language_prompt: string
  confidence: number
  warnings: string[]
  cached: boolean
  transcript_language: string | null
  was_translated: boolean
}

export function useVideoStrategy() {
  const [videoUrl, setVideoUrl] = useState('')
  const [isProcessingVideo, setIsProcessingVideo] = useState(false)
  const [videoResult, setVideoResult] = useState<VideoResult | null>(null)
  const [videoError, setVideoError] = useState<string | null>(null)

  const processVideo = useCallback(async (
    url: string,
    model: string,
    targetSymbol?: string,
    targetTimeframe?: string,
  ): Promise<VideoResult | null> => {
    setIsProcessingVideo(true)
    setVideoError(null)
    setVideoResult(null)

    try {
      const body: Record<string, string> = {
        youtube_url: url,
        model,
      }
      if (targetSymbol) body.target_symbol = targetSymbol
      if (targetTimeframe) body.target_timeframe = targetTimeframe

      const resp = await fetch(`${API_BASE_URL}/api/process-video`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!resp.ok) {
        const text = await resp.text()
        setVideoError(`Server error (${resp.status}): ${text}`)
        return null
      }

      const data = await resp.json()

      if (!data.success) {
        setVideoError(data.errors?.join(', ') || 'Failed to extract strategy from video')
        return null
      }

      const result: VideoResult = {
        video_id: data.video_id,
        title: data.title,
        channel: data.channel,
        strategy_name: data.strategy_name,
        strategy_description: data.strategy_description,
        natural_language_prompt: data.natural_language_prompt,
        confidence: data.confidence,
        warnings: data.warnings || [],
        cached: data.cached,
        transcript_language: data.transcript_language,
        was_translated: data.was_translated,
      }

      setVideoResult(result)
      return result
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      setVideoError(`Network error: ${msg}`)
      return null
    } finally {
      setIsProcessingVideo(false)
    }
  }, [])

  const resetVideo = useCallback(() => {
    setVideoUrl('')
    setVideoResult(null)
    setVideoError(null)
  }, [])

  return {
    videoUrl,
    setVideoUrl,
    isProcessingVideo,
    videoResult,
    videoError,
    processVideo,
    resetVideo,
  }
}
