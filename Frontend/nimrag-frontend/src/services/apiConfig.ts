const DEFAULT_API_BASE_URL = '/api/v1'

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

export function buildWebSocketUrl(): string {
  const explicitUrl = import.meta.env.VITE_WS_URL
  if (explicitUrl) {
    return explicitUrl
  }

  if (API_BASE_URL.startsWith('/')) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws`
  }

  const origin = API_BASE_URL.replace(/\/api\/v1$/, '')
  if (origin.startsWith('https://')) {
    return `${origin.replace('https://', 'wss://')}/ws`
  }

  return `${origin.replace('http://', 'ws://')}/ws`
}