import { getAppConfig } from '../services/appConfig'
import type { AppConfig } from '../types/appConfig'

export const DEFAULT_APP_CONFIG: AppConfig = {
  version: 1,
  system: {
    location_name: 'Stuttgart',
    latitude: 48.7758,
    longitude: 9.1829,
    units: 'metric',
    theme: 'dark',
    weather_refresh_seconds: 900,
    updated_at: null,
  },
  widgets: {
    weather: { refresh_seconds: 900 },
    news: { ressort: null, regions: [1], refresh_seconds: 3600 },
    camera: { preferred_device_id: null, preferred_device_label: null },
    market: { symbols: ['AAPL', 'MSFT', 'NVDA', 'BTC/USD', 'ETH/USD'], refresh_seconds: 900 },
  },
}

let appConfigPromise: Promise<AppConfig> | null = null

export function loadAppConfig(): Promise<AppConfig> {
  if (appConfigPromise === null) {
    appConfigPromise = getAppConfig().catch(() => DEFAULT_APP_CONFIG)
  }
  return appConfigPromise
}

export function resetAppConfigCache(): void {
  appConfigPromise = null
}