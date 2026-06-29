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
  | 'toggle_edit_mode'
  | 'delete_widget'
  | 'begin_drag'
  | 'drop_widget'

export interface UIActionArguments {
  cell_index?: number | null
  widget_type?: string | null
  mode?: UIActionMode | null
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