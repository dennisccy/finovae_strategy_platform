/**
 * API client for the model picker.
 *
 * Fetches GET /api/models — the single source of truth for selectable models
 * lives in apps/backend/shared/model_catalog.py and is served by that endpoint.
 * The frontend no longer hardcodes model ids.
 */

const API_BASE = import.meta.env.VITE_API_URL || ''

export interface ModelOption {
  value: string
  label: string
  default: boolean
}

// Used only when /api/models is unreachable, so the picker still works offline.
// Mirrors the backend catalog's default id.
export const FALLBACK_MODEL = 'gpt-5.4-mini'

const FALLBACK_MODELS: ModelOption[] = [
  { value: FALLBACK_MODEL, label: 'GPT-5.4 Mini', default: true },
]

export async function getModels(): Promise<ModelOption[]> {
  try {
    const res = await fetch(`${API_BASE}/api/models`)
    if (!res.ok) return FALLBACK_MODELS
    const data = await res.json()
    const models = Array.isArray(data?.models) ? (data.models as ModelOption[]) : []
    return models.length > 0 ? models : FALLBACK_MODELS
  } catch {
    return FALLBACK_MODELS
  }
}

export function defaultModelId(models: ModelOption[]): string {
  return models.find(m => m.default)?.value ?? models[0]?.value ?? FALLBACK_MODEL
}
