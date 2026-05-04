export type InputSourceType = 'gesture' | 'voice' | 'musical_audio' | 'dev' | 'keyboard'
export type CommandMatchOutcome = 'accepted' | 'suppressed' | 'unmapped' | 'disabled'
export type UIActionMode = 'grid' | 'shop' | 'arrange'

export type UIActionType =
  | 'move_focus_left'
  | 'move_focus_right'
  | 'move_focus_up'
  | 'move_focus_down'
  | 'focus_grid_cell'
  | 'focus_widget_type'
  | 'toggle_shop'
  | 'open_shop'
  | 'close_shop'
  | 'primary_click'
  | 'confirm_selection'
  | 'secondary_select'
  | 'enter_arrange_mode'
  | 'exit_arrange_mode'
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

export interface UIActionArguments {
  cell_index?: number | null
  widget_type?: string | null
  mode?: UIActionMode | null
}

export interface UIActionRequestedPayload {
  action: UIActionType
  timestamp: string
  input_source: InputSourceType
  raw_input: string
  action_args: UIActionArguments
  metadata: Record<string, unknown>
}

export interface CommandMatchEvaluatedPayload {
  input_source: InputSourceType
  raw_input: string
  timestamp: string
  outcome: CommandMatchOutcome
  action: UIActionType | null
  reason: string | null
  action_args: UIActionArguments
  metadata: Record<string, unknown>
}

export interface InputActionMapping {
  input_source: InputSourceType
  raw_input: string
  action: UIActionType
  enabled: boolean
  action_args: UIActionArguments
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
