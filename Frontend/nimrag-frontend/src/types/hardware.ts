export interface SystemStatusResponse {
  status: string
  version: string
  database_path: string
  config_entries: number
  weather_cache_entries: number
}

export interface GestureStatusResponse {
  available: boolean
  running: boolean
  camera_index: number | null
  last_gesture: string | null
  last_gesture_at: string | null
  last_confidence: number | null
  last_tracking_source: string | null
  debug_frame_available: boolean
  last_error: string | null
}

export interface GestureFrameResponse {
  image: string
}

export interface LEDStateResponse {
  message: string
  red: number
  green: number
  blue: number
  brightness: number
  available: boolean
  mode: 'hardware' | 'mock'
  last_error: string | null
}

export interface VoiceStatusResponse {
  message: string
  available: boolean
  running: boolean
  mode: 'skeleton' | 'unavailable'
  provider: string | null
  device_index: number | null
  last_command: string | null
  last_command_at: string | null
  last_error: string | null
}

export interface RealtimeEvent<TPayload = Record<string, unknown>> {
  eventType: string
  payload: TPayload
}