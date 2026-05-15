import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The shared Aplhion dev/start scripts export NEXT_PUBLIC_API_URL (full URL)
// and NEXT_PUBLIC_API_PORT (offset-aware). Fall back to :8000 for a bare
// `npm run dev` / `vite` invocation.
const apiTarget =
  process.env.NEXT_PUBLIC_API_URL ||
  `http://localhost:${process.env.NEXT_PUBLIC_API_PORT || 8000}`

export default defineConfig({
  plugins: [react()],
  server: {
    // Default for bare `vite` / `npm run dev`; the next-vite-shim passes
    // `--port <FRONTEND_PORT>` which overrides this (CLI > config).
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
