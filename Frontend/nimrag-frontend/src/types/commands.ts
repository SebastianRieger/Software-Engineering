import type { InputActionConfig } from './interactions'

export type CommandModalityType = 'gesture' | 'voice' | 'musical_audio' | 'keyboard' | 'dev'

export interface CommandModalitySettings {
  enabled: boolean
  active_training_artifact_id: string | null
  metadata: Record<string, unknown>
}

export interface CommandDevicePreferences {
  gesture_camera_index: number | null
  voice_device_index: number | null
  musical_audio_device_index: number | null
}

export interface CommandProfile {
  profile_id: string
  display_name: string
  description: string | null
  input_action_config: InputActionConfig
  modality_settings: Record<CommandModalityType, CommandModalitySettings>
  device_preferences: CommandDevicePreferences
  updated_at: string | null
}

export interface CommandProfilesConfig {
  active_profile_id: string
  profiles: CommandProfile[]
  updated_at: string | null
}

export interface CommandProfilesConfigEnvelope {
  config: CommandProfilesConfig
}

export interface MusicalAudioConfig {
  enabled: boolean
  device_index: number
  sample_rate: number
  block_size: number
  queue_max_chunks: number
  silence_threshold: number
  pitch_confidence_threshold: number
  command_cooldown_seconds: number
  min_pattern_notes: number
  max_pattern_window_seconds: number
  active_artifact_id: string | null
  updated_at: string | null
}

export interface MusicalAudioConfigEnvelope {
  config: MusicalAudioConfig
}

export interface MusicalAudioNoteEvent {
  relative_pitch_semitones: number
  relative_time_seconds: number
  duration_seconds: number | null
  confidence: number | null
}

export interface MusicalAudioTrainingArtifact {
  artifact_id: string
  profile_id: string
  raw_input: string
  display_name: string
  source_hint: 'whistle' | 'voice' | 'instrument' | 'unknown'
  notes: MusicalAudioNoteEvent[]
  match_threshold: number
  minimum_confidence: number
  sample_count: number
  enabled: boolean
  created_at: string | null
  updated_at: string | null
  metadata: Record<string, unknown>
}

export interface MusicalAudioTrainingArtifactEnvelope {
  artifact: MusicalAudioTrainingArtifact
}

export interface MusicalAudioTrainingArtifactListEnvelope {
  artifacts: MusicalAudioTrainingArtifact[]
}
