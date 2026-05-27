import { afterEach, describe, expect, it, vi } from 'vitest'

async function loadApiConfig() {
  vi.resetModules()
  return import('@/services/apiConfig')
}

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

describe('apiConfig service', () => {
  it('normalizes the configured API base URL and builds API paths', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com/api/v1/')

    const { API_BASE_URL, buildApiUrl } = await loadApiConfig()

    expect(API_BASE_URL).toBe('https://api.example.com/api/v1')
    expect(buildApiUrl('weather/current')).toBe('https://api.example.com/api/v1/weather/current')
  })

  it('prefers an explicit websocket URL when configured', async () => {
    vi.stubEnv('VITE_WS_URL', 'wss://socket.example.com/ws')

    const { buildWebSocketUrl } = await loadApiConfig()

    expect(buildWebSocketUrl()).toBe('wss://socket.example.com/ws')
  })

  it('derives a websocket URL from a relative API base path', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')

    const { buildWebSocketUrl } = await loadApiConfig()
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'

    expect(buildWebSocketUrl()).toBe(`${protocol}//${window.location.host}/ws`)
  })

  it('derives a secure websocket URL from an HTTPS API origin', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://mirror.example.com/api/v1')

    const { buildWebSocketUrl } = await loadApiConfig()

    expect(buildWebSocketUrl()).toBe('wss://mirror.example.com/ws')
  })

  it('derives an unencrypted websocket URL from an HTTP API origin', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://mirror.example.com/api/v1')

    const { buildWebSocketUrl } = await loadApiConfig()

    expect(buildWebSocketUrl()).toBe('ws://mirror.example.com/ws')
  })
})