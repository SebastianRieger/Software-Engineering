export type InputSourceType = 'gesture' | 'voice' | 'musical_audio' | 'dev' | 'keyboard'
export type CommandMatchOutcome = 'accepted' | 'suppressed' | 'unmapped' | 'disabled'

export type UIActionType =
  | 'move_focus_left'
  | 'move_focus_right'
  | 'move_focus_up'
  | 'move_focus_down'
  | 'toggle_shop'
  | 'primary_click'
  | 'secondary_select'
  | 'resize_expand'
  | 'resize_shrink'
  | 'move_selected_widget'
  | 'cancel_selection'

export interface FocusState {
  row: number
  col: number
  widgetId: string | null
}

export interface GestureDetectedPayload {
  gesture: string
  timestamp: string
  source: 'camera'
  hand: string | null
  confidence: number | null
  tracking_source: string | null
}

export interface RawInputDetectedPayload {
  input_source: InputSourceType
  raw_input: string
  timestamp: string
  metadata: Record<string, unknown>
}

export interface UIActionRequestedPayload {
  action: UIActionType
  timestamp: string
  input_source: InputSourceType
  raw_input: string
  metadata: Record<string, unknown>
}

export interface CommandMatchEvaluatedPayload {
  input_source: InputSourceType
  raw_input: string
  timestamp: string
  outcome: CommandMatchOutcome
  action: UIActionType | null
  reason: string | null
  metadata: Record<string, unknown>
}

export interface InputActionMapping {
  input_source: InputSourceType
  raw_input: string
  action: UIActionType
  enabled: boolean
  metadata: Record<string, unknown>
}

export interface InputActionConfig {
  mappings: InputActionMapping[]
  global_cooldown_seconds: number
  repeat_same_action_window_seconds: number
  source_priorities: Record<InputSourceType, number>
  updated_at: string | null
}

export interface InputActionConfigEnvelope {
  config: InputActionConfig
}
