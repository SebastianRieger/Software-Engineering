import { describe, expect, it } from 'vitest'

import type { ActiveWidgetMap } from '../types/widgets'
import type { FocusState } from '../types/interactions'
import { reduceInteractionState, type InteractionState } from '../utils/interactionReducer'

function buildState(overrides: Partial<InteractionState> = {}): InteractionState {
  return {
    activeWidgets: {},
    focusedState: { row: 1, col: 1, widgetId: null },
    selectedWidgetId: null,
    isArrangeMode: false,
    shopVisible: false,
    isCalibrationMode: false,
    ...overrides,
  }
}

function buildWidgetState(): { activeWidgets: ActiveWidgetMap; focusedState: FocusState } {
  const activeWidgets: ActiveWidgetMap = {
    'weather-1-1': {
      widget_id: 'weather-1-1',
      widget_type: 'weather',
      row: 1,
      col: 1,
      row_span: 1,
      col_span: 1,
      cell_id: 1,
      title: 'Wetter',
      settings: {},
    },
  }

  return {
    activeWidgets,
    focusedState: { row: 1, col: 1, widgetId: 'weather-1-1' },
  }
}

describe('reduceInteractionState', () => {
  it('moves focus in normal mode', () => {
    const result = reduceInteractionState(buildState(), 'move_focus_right', {
      shopCurrentWidgetType: null,
    })

    expect(result.state.focusedState.col).toBe(2)
    expect(result.effects).toEqual([])
  })

  it('navigates the shop instead of moving focus while the shop is open', () => {
    const result = reduceInteractionState(buildState({ shopVisible: true }), 'move_focus_left', {
      shopCurrentWidgetType: 'weather',
    })

    expect(result.state.focusedState.col).toBe(1)
    expect(result.effects).toEqual([{ type: 'shop-navigation', direction: 'prev' }])
  })

  it('places the current shop widget into an empty focused cell', () => {
    const result = reduceInteractionState(buildState({ shopVisible: true }), 'primary_click', {
      shopCurrentWidgetType: 'weather',
    })

    expect(Object.values(result.state.activeWidgets)).toHaveLength(1)
    expect(Object.values(result.state.activeWidgets)[0]?.widget_type).toBe('weather')
    expect(result.state.shopVisible).toBe(false)
    expect(result.effects).toEqual([{ type: 'persist-layout' }])
  })

  it('moves the selected widget in arrange mode and requests persistence', () => {
    const { activeWidgets, focusedState } = buildWidgetState()
    const result = reduceInteractionState(buildState({
      activeWidgets,
      focusedState,
      selectedWidgetId: 'weather-1-1',
      isArrangeMode: true,
    }), 'move_focus_right', {
      shopCurrentWidgetType: null,
    })

    expect(result.state.activeWidgets['weather-1-1']?.col).toBe(2)
    expect(result.effects).toEqual([{ type: 'persist-layout' }])
  })
})