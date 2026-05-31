export type NewsRessort = 'inland' | 'ausland' | 'wirtschaft' | 'sport' | 'video' | 'investigativ' | 'wissen'

export interface SystemAppConfig {
  location_name: string | null
  latitude: number
  longitude: number
  units: 'metric' | 'imperial'
  theme: 'dark' | 'light' | 'system'
  weather_refresh_seconds: number
  updated_at?: string | null
}

export interface WeatherWidgetConfig {
  refresh_seconds: number
}

export interface NewsWidgetConfig {
  ressort: NewsRessort | null
  regions: number[]
  refresh_seconds: number
}

export interface CameraWidgetConfig {
  preferred_device_id: string | null
  preferred_device_label: string | null
}

export interface MarketWidgetConfig {
  symbols: string[]
}
export interface NinaWidgetConfig {
  ars: string
  refresh_seconds: number
}

export interface WidgetDefaultsConfig {
  weather: WeatherWidgetConfig
  news: NewsWidgetConfig
  camera: CameraWidgetConfig
  market: MarketWidgetConfig
  nina?: NinaWidgetConfig
}

export interface AppConfig {
  version: number
  system: SystemAppConfig
  widgets: WidgetDefaultsConfig
}

export interface AppConfigEnvelope {
  config: AppConfig
}