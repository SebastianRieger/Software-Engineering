const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1'

function normalizeBaseUrl(value: string): string {
  return value.replace(/\/$/, '')
}

export const API_BASE_URL = normalizeBaseUrl(
  import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
)

export function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}