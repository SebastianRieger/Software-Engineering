export type WidgetSettings = Record<string, unknown>

export interface WidgetConfig {
  widget_id: string
  widget_type: string
  cell_id: number
  title: string | null
  settings: WidgetSettings
}

export interface LayoutConfig {
  version: number
  widgets: WidgetConfig[]
  updated_at: string | null
}

export interface LayoutConfigEnvelope {
  profile: string
  config: LayoutConfig
}

export type UnitSystem = 'metric' | 'imperial'
export type ThemeMode = 'dark' | 'light' | 'system'

export interface SystemConfig {
  location_name: string | null
  latitude: number
  longitude: number
  units: UnitSystem
  theme: ThemeMode
  weather_refresh_seconds: number
  updated_at: string | null
}

export interface SystemConfigEnvelope {
  config: SystemConfig
}