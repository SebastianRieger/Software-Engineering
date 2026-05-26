import { ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import { useActionDispatcher } from '@/composables/useActionDispatcher'
import type { UIActionRequestedPayload } from '@/types/interactions'

function createPayload(action: UIActionRequestedPayload['action']): UIActionRequestedPayload {
  return {
    action,
    timestamp: new Date().toISOString(),
    input_source: 'gesture',
    raw_input: action,
    action_args: {},
    metadata: {},
  }
}

function createPayloadWithArgs(
  action: UIActionRequestedPayload['action'],
  action_args: UIActionRequestedPayload['action_args'],
): UIActionRequestedPayload {
  return {
    ...createPayload(action),
    action_args,
  }
}

describe('useActionDispatcher', () => {
  it('moves focus right across visible cells', () => {
    const dispatcher = useActionDispatcher({
      isShopOpen: ref(false),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode: ref(false),
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: () => true,
      moduleShopRef: ref(null),
    })

    expect(dispatcher.focusedCellId.value).toBe(1)
    expect(dispatcher.dispatchAction(createPayload('move_focus_right'))).toBe(true)
    expect(dispatcher.focusedCellId.value).toBe(2)
  })

  it('uses the module shop for horizontal navigation while the shop is open', () => {
    const nextModule = vi.fn()
    const prevModule = vi.fn()

    const dispatcher = useActionDispatcher({
      isShopOpen: ref(true),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode: ref(false),
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: () => true,
      moduleShopRef: ref({
        addCurrentWidgetToCell: vi.fn(),
        nextModule,
        prevModule,
      }),
    })

    dispatcher.dispatchAction(createPayload('move_focus_right'))
    dispatcher.dispatchAction(createPayload('move_focus_left'))

    expect(nextModule).toHaveBeenCalledOnce()
    expect(prevModule).toHaveBeenCalledOnce()
    expect(dispatcher.focusedCellId.value).toBe(1)
  })

  it('confirms the focused cell through the module shop and closes the shop', () => {
    const addCurrentWidgetToCell = vi.fn()
    const closeShop = vi.fn()
    const isShopOpen = ref(true)

    const dispatcher = useActionDispatcher({
      isShopOpen,
      openShop: vi.fn(),
      closeShop,
      toggleShop: vi.fn(),
      isEditMode: ref(false),
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: (cellId) => cellId === 2,
      moduleShopRef: ref({
        addCurrentWidgetToCell,
        nextModule: vi.fn(),
        prevModule: vi.fn(),
      }),
    })

    dispatcher.dispatchAction(createPayloadWithArgs('focus_grid_cell', { cell_index: 2 }))
    expect(dispatcher.dispatchAction(createPayload('confirm_selection'))).toBe(true)

    expect(addCurrentWidgetToCell).toHaveBeenCalledWith(2)
    expect(closeShop).toHaveBeenCalledOnce()
  })

  it('opens and closes shop actions directly', () => {
    const openShop = vi.fn()
    const closeShop = vi.fn()
    const toggleShop = vi.fn()

    const dispatcher = useActionDispatcher({
      isShopOpen: ref(false),
      openShop,
      closeShop,
      toggleShop,
      isEditMode: ref(false),
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: () => true,
      moduleShopRef: ref(null),
    })

    dispatcher.dispatchAction(createPayload('open_shop'))
    dispatcher.dispatchAction(createPayload('close_shop'))
    dispatcher.dispatchAction(createPayload('toggle_shop'))

    expect(openShop).toHaveBeenCalledOnce()
    expect(closeShop).toHaveBeenCalledOnce()
    expect(toggleShop).toHaveBeenCalledOnce()
  })

  it('returns false when focusing a missing or hidden grid cell', () => {
    const dispatcher = useActionDispatcher({
      isShopOpen: ref(false),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode: ref(false),
      visibleCellIds: () => [1, 2, 3],
      isCellAvailable: () => true,
      moduleShopRef: ref(null),
    })

    expect(dispatcher.dispatchAction(createPayloadWithArgs('focus_grid_cell', {}))).toBe(false)
    expect(dispatcher.dispatchAction(createPayloadWithArgs('focus_grid_cell', { cell_index: 9 }))).toBe(false)
  })

  it('returns false when confirming a selection without a usable shop target', () => {
    const closedShopDispatcher = useActionDispatcher({
      isShopOpen: ref(false),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode: ref(false),
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: () => true,
      moduleShopRef: ref(null),
    })

    expect(closedShopDispatcher.dispatchAction(createPayload('confirm_selection'))).toBe(false)

    const unavailableCellDispatcher = useActionDispatcher({
      isShopOpen: ref(true),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode: ref(false),
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: () => false,
      moduleShopRef: ref({
        addCurrentWidgetToCell: vi.fn(),
        nextModule: vi.fn(),
        prevModule: vi.fn(),
      }),
    })

    expect(unavailableCellDispatcher.dispatchAction(createPayload('confirm_selection'))).toBe(false)

    const missingModuleShopDispatcher = useActionDispatcher({
      isShopOpen: ref(true),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode: ref(false),
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: () => true,
      moduleShopRef: ref(null),
    })

    expect(missingModuleShopDispatcher.dispatchAction(createPayload('primary_click'))).toBe(false)
  })

  it('supports arrange-mode and resize actions when optional handlers exist', () => {
    const setEditMode = vi.fn()
    const resizeCell = vi.fn()

    const dispatcher = useActionDispatcher({
      isShopOpen: ref(false),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode: ref(false),
      setEditMode,
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: () => true,
      resizeCell,
      moduleShopRef: ref(null),
    })

    expect(dispatcher.dispatchAction(createPayload('enter_arrange_mode'))).toBe(true)
    expect(dispatcher.dispatchAction(createPayload('exit_arrange_mode'))).toBe(true)
    expect(dispatcher.dispatchAction(createPayload('resize_expand'))).toBe(true)
    expect(dispatcher.dispatchAction(createPayload('resize_shrink'))).toBe(true)

    expect(setEditMode).toHaveBeenNthCalledWith(1, true)
    expect(setEditMode).toHaveBeenNthCalledWith(2, false)
    expect(resizeCell).toHaveBeenNthCalledWith(1, 1, 'expand')
    expect(resizeCell).toHaveBeenNthCalledWith(2, 1, 'shrink')
  })

  it('returns false for optional actions when the corresponding handlers are missing', () => {
    const dispatcher = useActionDispatcher({
      isShopOpen: ref(false),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode: ref(false),
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: () => true,
      moduleShopRef: ref(null),
    })

    expect(dispatcher.dispatchAction(createPayload('enter_arrange_mode'))).toBe(false)
    expect(dispatcher.dispatchAction(createPayload('exit_arrange_mode'))).toBe(false)
    expect(dispatcher.dispatchAction(createPayload('resize_expand'))).toBe(false)
    expect(dispatcher.dispatchAction(createPayload('resize_shrink'))).toBe(false)
  })

  it('ignores unrelated or malformed realtime events', () => {
    const dispatcher = useActionDispatcher({
      isShopOpen: ref(false),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode: ref(false),
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: () => true,
      moduleShopRef: ref(null),
    })

    expect(
      dispatcher.handleRealtimeEvent({
        eventType: 'Pong',
        payload: { message: 'still alive' },
      }),
    ).toBe(false)

    expect(
      dispatcher.handleRealtimeEvent({
        eventType: 'UIActionRequested',
        payload: null,
      }),
    ).toBe(false)
  })
})