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

export interface UIActionRequestedPayload {
  action: UIActionType
  timestamp: string
  input_source: 'gesture' | 'voice' | 'dev' | 'keyboard'
  raw_input: string
  metadata: Record<string, unknown>
}
