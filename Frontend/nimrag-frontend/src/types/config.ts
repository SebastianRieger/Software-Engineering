export type WidgetSettings = Record<string, unknown>

export type ClockTimeFormat = '12h' | '24h'
export type ClockTimezoneMode = 'browser' | 'utc'

export interface ClockWidgetSettings extends WidgetSettings {
  format?: ClockTimeFormat
  showSeconds?: boolean
  timezoneMode?: ClockTimezoneMode
}

export interface HardwareStatusWidgetSettings extends WidgetSettings {
  showPreview?: boolean
  autoRefresh?: boolean
}

export interface WidgetPlacement {
  row: number
  col: number
  row_span: number
  col_span: number
  cell_id?: number | null
}

export interface WidgetConfig extends WidgetPlacement {
  widget_id: string
  widget_type: string
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