import { buildApiUrl } from './apiConfig'
import type { LayoutConfig, LayoutConfigEnvelope, SystemConfig, SystemConfigEnvelope } from '../types/config'
import type { WeatherCurrentResponse } from '../types/weather'

type QueryValue = string | number | boolean | null | undefined

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function buildQuery(params: Record<string, QueryValue>): string {
  const searchParams = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return
    }
    searchParams.set(key, String(value))
  })

  const query = searchParams.toString()
  return query ? `?${query}` : ''
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...(init?.headers ?? {}),
    },
  })

  const responseText = await response.text()
  const responseData = responseText ? JSON.parse(responseText) : null

  if (!response.ok) {
    const message = typeof responseData?.detail === 'string'
      ? responseData.detail
      : `Request failed with status ${response.status}`
    throw new ApiError(message, response.status)
  }

  return responseData as T
}

export const apiClient = {
  getLayout(profile = 'default'): Promise<LayoutConfigEnvelope> {
    return requestJson<LayoutConfigEnvelope>(`/config/layout${buildQuery({ profile })}`)
  },

  saveLayout(layout: LayoutConfig, profile = 'default'): Promise<LayoutConfigEnvelope> {
    return requestJson<LayoutConfigEnvelope>(`/config/layout${buildQuery({ profile })}`, {
      method: 'PUT',
      body: JSON.stringify(layout),
    })
  },

  getSystemConfig(): Promise<SystemConfigEnvelope> {
    return requestJson<SystemConfigEnvelope>('/config/system')
  },

  saveSystemConfig(config: SystemConfig): Promise<SystemConfigEnvelope> {
    return requestJson<SystemConfigEnvelope>('/config/system', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  },

  getCurrentWeather(params?: { lat?: number; lon?: number }): Promise<WeatherCurrentResponse> {
    return requestJson<WeatherCurrentResponse>(`/weather/current${buildQuery(params ?? {})}`)
  },
}