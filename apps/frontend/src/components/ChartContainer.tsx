import { useState, useRef, useEffect, type ReactElement } from 'react'
import { ResponsiveContainer } from 'recharts'

interface ChartContainerProps {
  width?: string | number
  height: string | number
  children: ReactElement
}

/**
 * Wrapper around Recharts ResponsiveContainer that only renders
 * when the container has non-zero dimensions. This prevents the
 * "width(0) and height(0)" warning when charts are inside a
 * display:none parent (e.g. inactive session tabs).
 */
export function ChartContainer({ width = '100%', height, children }: ChartContainerProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        setIsVisible(width > 0 && height > 0)
      }
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={ref} style={{ width, height: typeof height === 'number' ? `${height}px` : height }}>
      {isVisible && (
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      )}
    </div>
  )
}
