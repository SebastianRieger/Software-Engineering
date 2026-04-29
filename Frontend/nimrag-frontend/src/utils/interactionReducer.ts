import type { ActiveWidgetMap } from '../types/widgets'
import type { FocusState, UIActionType } from '../types/interactions'
import {
  createFocusState,
  findWidgetAtCell,
  getFocusStateForWidget,
  moveFocus,
  moveWidgetByOffset,
  resizeWidget,
  upsertWidget,
} from './layout'

export interface InteractionState {
  activeWidgets: ActiveWidgetMap
  focusedState: FocusState
  selectedWidgetId: string | null
  isArrangeMode: boolean
  shopVisible: boolean
  isCalibrationMode: boolean
}

export interface InteractionReducerContext {
  shopCurrentWidgetType: string | null
}

export type InteractionReducerEffect =
  | { type: 'persist-layout' }
  | { type: 'shop-navigation'; direction: 'next' | 'prev' }

export interface InteractionReducerResult {
  state: InteractionState
  effects: InteractionReducerEffect[]
  error: string | null
}

function getFocusedWidget(state: InteractionState) {
  return state.focusedState.widgetId
    ? state.activeWidgets[state.focusedState.widgetId] ?? null
    : findWidgetAtCell(state.activeWidgets, state.focusedState.row, state.focusedState.col)
}

function syncInteractionState(
  state: InteractionState,
  activeWidgets: ActiveWidgetMap,
  target?: { row: number; col: number },
): InteractionState {
  const row = target?.row ?? state.focusedState.row
  const col = target?.col ?? state.focusedState.col
  const focusedState = createFocusState(row, col, activeWidgets)

  if (state.selectedWidgetId && !activeWidgets[state.selectedWidgetId]) {
    return {
      ...state,
      activeWidgets,
      focusedState,
      selectedWidgetId: null,
      isArrangeMode: false,
    }
  }

  return {
    ...state,
    activeWidgets,
    focusedState,
  }
}

function enterArrangeMode(state: InteractionState, widgetId: string): InteractionState {
  const widget = state.activeWidgets[widgetId]
  if (!widget) {
    return state
  }

  return {
    ...state,
    selectedWidgetId: widgetId,
    isArrangeMode: true,
    shopVisible: false,
    focusedState: createFocusState(widget.row, widget.col, state.activeWidgets),
  }
}

function exitArrangeMode(state: InteractionState): InteractionState {
  return {
    ...state,
    isArrangeMode: false,
    selectedWidgetId: null,
  }
}

function addFocusedWidget(state: InteractionState, widgetType: string): InteractionReducerResult {
  try {
    const activeWidgets = upsertWidget(state.activeWidgets, state.focusedState, widgetType)
    return {
      state: {
        ...syncInteractionState({
          ...state,
          shopVisible: false,
        }, activeWidgets),
      },
      effects: [{ type: 'persist-layout' }],
      error: null,
    }
  } catch {
    return {
      state,
      effects: [],
      error: `Widget konnte nicht platziert werden: ${widgetType}`,
    }
  }
}

function moveSelectedWidget(
  state: InteractionState,
  rowOffset: number,
  colOffset: number,
): InteractionReducerResult {
  if (!state.selectedWidgetId) {
    return { state, effects: [], error: null }
  }

  const activeWidgets = moveWidgetByOffset(state.activeWidgets, state.selectedWidgetId, rowOffset, colOffset)
  if (activeWidgets === state.activeWidgets) {
    return { state, effects: [], error: null }
  }

  return {
    state: syncInteractionState(state, activeWidgets),
    effects: [{ type: 'persist-layout' }],
    error: null,
  }
}

function resizeSelectedWidget(
  state: InteractionState,
  mode: 'expand' | 'shrink',
): InteractionReducerResult {
  if (!state.selectedWidgetId) {
    return { state, effects: [], error: null }
  }

  const activeWidgets = resizeWidget(state.activeWidgets, state.selectedWidgetId, mode)
  if (activeWidgets === state.activeWidgets) {
    return { state, effects: [], error: null }
  }

  return {
    state: syncInteractionState(state, activeWidgets),
    effects: [{ type: 'persist-layout' }],
    error: null,
  }
}

function confirmShopSelection(
  state: InteractionState,
  context: InteractionReducerContext,
): InteractionReducerResult | null {
  if (!state.shopVisible) {
    return null
  }

  if (getFocusedWidget(state)) {
    return { state, effects: [], error: null }
  }

  if (!context.shopCurrentWidgetType) {
    return { state, effects: [], error: null }
  }

  return addFocusedWidget(state, context.shopCurrentWidgetType)
}

export function reduceInteractionState(
  state: InteractionState,
  action: UIActionType,
  context: InteractionReducerContext,
): InteractionReducerResult {
  if (state.isCalibrationMode) {
    return { state, effects: [], error: null }
  }

  if (state.isArrangeMode && state.selectedWidgetId) {
    if (action === 'move_focus_left') {
      return moveSelectedWidget(state, 0, -1)
    }
    if (action === 'move_focus_right') {
      return moveSelectedWidget(state, 0, 1)
    }
    if (action === 'move_focus_up') {
      return moveSelectedWidget(state, -1, 0)
    }
    if (action === 'move_focus_down') {
      return moveSelectedWidget(state, 1, 0)
    }
  }

  switch (action) {
    case 'move_focus_left':
      if (state.shopVisible) {
        return { state, effects: [{ type: 'shop-navigation', direction: 'prev' }], error: null }
      }
      return {
        state: {
          ...state,
          focusedState: moveFocus(state.activeWidgets, state.focusedState, 0, -1),
        },
        effects: [],
        error: null,
      }
    case 'move_focus_right':
      if (state.shopVisible) {
        return { state, effects: [{ type: 'shop-navigation', direction: 'next' }], error: null }
      }
      return {
        state: {
          ...state,
          focusedState: moveFocus(state.activeWidgets, state.focusedState, 0, 1),
        },
        effects: [],
        error: null,
      }
    case 'move_focus_up':
      return {
        state: {
          ...state,
          focusedState: moveFocus(state.activeWidgets, state.focusedState, -1, 0),
        },
        effects: [],
        error: null,
      }
    case 'move_focus_down':
      return {
        state: {
          ...state,
          focusedState: moveFocus(state.activeWidgets, state.focusedState, 1, 0),
        },
        effects: [],
        error: null,
      }
    case 'toggle_shop':
      return {
        state: state.isArrangeMode
          ? exitArrangeMode(state)
          : { ...state, shopVisible: !state.shopVisible },
        effects: [],
        error: null,
      }
    case 'primary_click': {
      const confirmation = confirmShopSelection(state, context)
      if (confirmation) {
        return confirmation
      }

      const focusedWidget = getFocusedWidget(state)
      if (focusedWidget) {
        return {
          state: {
            ...state,
            selectedWidgetId: focusedWidget.widget_id,
            focusedState: getFocusStateForWidget(state.activeWidgets, focusedWidget.widget_id),
          },
          effects: [],
          error: null,
        }
      }

      return {
        state: { ...state, shopVisible: true },
        effects: [],
        error: null,
      }
    }
    case 'secondary_select': {
      const confirmation = confirmShopSelection(state, context)
      if (confirmation) {
        return confirmation
      }
      if (state.isArrangeMode) {
        return {
          state: exitArrangeMode(state),
          effects: [],
          error: null,
        }
      }

      const focusedWidget = getFocusedWidget(state)
      if (!focusedWidget) {
        return { state, effects: [], error: null }
      }
      return {
        state: enterArrangeMode(state, focusedWidget.widget_id),
        effects: [],
        error: null,
      }
    }
    case 'resize_expand':
      return state.isArrangeMode ? resizeSelectedWidget(state, 'expand') : { state, effects: [], error: null }
    case 'resize_shrink':
      return state.isArrangeMode ? resizeSelectedWidget(state, 'shrink') : { state, effects: [], error: null }
    case 'cancel_selection':
      return {
        state: {
          ...exitArrangeMode(state),
          shopVisible: false,
        },
        effects: [],
        error: null,
      }
    case 'move_selected_widget':
      return { state, effects: [], error: null }
  }
}