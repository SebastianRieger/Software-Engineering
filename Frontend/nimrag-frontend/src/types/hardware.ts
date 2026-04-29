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
  camera_name: string | null
  last_gesture: string | null
  last_gesture_at: string | null
  last_confidence: number | null
  last_tracking_source: string | null
  debug_frame_available: boolean
  last_error: string | null
}

export interface GestureCameraDevice {
  index: number
  name: string
  available: boolean
  backend: string | null
}

export interface GestureCameraListResponse {
  devices: GestureCameraDevice[]
}

export interface GestureFrameResponse {
  image: string
}

export interface LEDColor {
  red: number
  green: number
  blue: number
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
  enabled: boolean
  running: boolean
  mode: 'skeleton' | 'unavailable' | 'direct-mic'
  provider: string | null
  device_index: number | null
  device_name: string | null
  sample_rate: number | null
  block_size: number | null
  queue_max_chunks: number | null
  commands: string[]
  partial_results_enabled: boolean
  command_cooldown_seconds: number | null
  chunks_processed: number
  chunks_dropped: number
  last_audio_level: number | null
  last_transcript: string | null
  last_command: string | null
  last_command_at: string | null
  last_error: string | null
}

export interface VoiceInputDevice {
  index: number
  name: string
  max_input_channels: number
  default_samplerate: number | null
  is_default: boolean
}

export interface VoiceInputDeviceListResponse {
  devices: VoiceInputDevice[]
}

export interface MusicalAudioStatusResponse {
  message: string
  available: boolean
  enabled: boolean
  running: boolean
  status_code:
    | 'unavailable'
    | 'ready'
    | 'running'
    | 'configuration_disabled'
    | 'no_active_artifact'
    | 'device_missing'
    | 'invalid_sample_rate'
    | 'permission_blocked'
    | 'runtime_start_failed'
    | 'runtime_running_no_matchable_artifacts'
  mode: 'unavailable' | 'direct-mic'
  provider: string | null
  active_profile_id: string | null
  device_index: number | null
  device_name: string | null
  sample_rate: number | null
  block_size: number | null
  queue_max_chunks: number | null
  active_artifact_id: string | null
  artifacts_loaded: number
  validated_device_index: number | null
  validated_sample_rate: number | null
  last_pitch_hz: number | null
  last_match: string | null
  last_match_score: number | null
  last_event_at: string | null
  last_error: string | null
  last_error_code: MusicalAudioStatusResponse['status_code'] | null
}

export interface MusicalAudioInputDevice {
  index: number
  name: string
  max_input_channels: number
  default_samplerate: number | null
  is_default: boolean
}

export interface MusicalAudioInputDeviceListResponse {
  devices: MusicalAudioInputDevice[]
}

export interface RealtimeEvent<TPayload = Record<string, unknown>> {
  eventType: string
  payload: TPayload
}