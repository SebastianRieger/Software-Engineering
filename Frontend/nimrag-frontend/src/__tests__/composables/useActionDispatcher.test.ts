import { nextTick, ref } from 'vue'
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
      isCellOccupied: () => false,
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
      isCellOccupied: () => false,
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
      isCellOccupied: () => false,
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
      isCellOccupied: () => false,
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
      isCellOccupied: () => false,
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
      isCellOccupied: () => false,
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
      isCellOccupied: () => false,
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
      isCellOccupied: () => false,
      moduleShopRef: ref(null),
    })

    expect(missingModuleShopDispatcher.dispatchAction(createPayload('primary_click'))).toBe(false)
  })

  it('supports arrange-mode and resize actions when optional handlers exist', () => {
    const isEditMode = ref(false)
    const setEditMode = vi.fn((value: boolean) => {
      isEditMode.value = value
    })
    const resizeCell = vi.fn()

    const dispatcher = useActionDispatcher({
      isShopOpen: ref(false),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode,
      setEditMode,
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: () => true,
      isCellOccupied: () => true,
      resizeCell,
      moduleShopRef: ref(null),
    })

    expect(dispatcher.dispatchAction(createPayload('enter_arrange_mode'))).toBe(true)
    expect(dispatcher.dispatchAction(createPayload('resize_expand'))).toBe(true)
    expect(dispatcher.dispatchAction(createPayload('resize_shrink'))).toBe(true)
    expect(dispatcher.dispatchAction(createPayload('exit_arrange_mode'))).toBe(true)

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
      isCellOccupied: () => false,
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
      isCellOccupied: () => false,
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

  it('opens the grid from the home view on move_focus_left', () => {
    const goToGrid = vi.fn()

    const dispatcher = useActionDispatcher({
      isShopOpen: ref(false),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode: ref(false),
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: () => true,
      isCellOccupied: () => false,
      moduleShopRef: ref(null),
      currentView: ref('home'),
      goToGrid,
    })

    expect(dispatcher.dispatchAction(createPayload('move_focus_left'))).toBe(true)
    expect(goToGrid).toHaveBeenCalledOnce()
  })

  it('uses circle to enter and exit edit mode from grid idle', () => {
    const isEditMode = ref(false)
    const setEditMode = vi.fn((value: boolean) => {
      isEditMode.value = value
    })
    const goToGrid = vi.fn()

    const dispatcher = useActionDispatcher({
      isShopOpen: ref(false),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode,
      setEditMode,
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: () => true,
      isCellOccupied: () => false,
      moduleShopRef: ref(null),
      currentView: ref('grid'),
      goToGrid,
    })

    expect(dispatcher.dispatchAction(createPayload('toggle_edit_mode'))).toBe(true)
    expect(goToGrid).toHaveBeenCalledOnce()
    expect(setEditMode).toHaveBeenLastCalledWith(true)
    expect(isEditMode.value).toBe(true)

    expect(dispatcher.dispatchAction(createPayload('toggle_edit_mode'))).toBe(true)
    expect(setEditMode).toHaveBeenLastCalledWith(false)
  })

  it('uses pinch close for empty-cell shop flow and widget placement', () => {
    const isShopOpen = ref(false)
    const openShop = vi.fn(() => {
      isShopOpen.value = true
    })
    const closeShop = vi.fn(() => {
      isShopOpen.value = false
    })
    const addCurrentWidgetToCell = vi.fn()

    const dispatcher = useActionDispatcher({
      isShopOpen,
      openShop,
      closeShop,
      toggleShop: vi.fn(),
      isEditMode: ref(true),
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: (cellId) => cellId === 1,
      isCellOccupied: () => false,
      moduleShopRef: ref({
        addCurrentWidgetToCell,
        nextModule: vi.fn(),
        prevModule: vi.fn(),
      }),
    })

    expect(dispatcher.dispatchAction(createPayload('primary_click'))).toBe(true)
    expect(openShop).toHaveBeenCalledOnce()
    expect(isShopOpen.value).toBe(true)

    expect(dispatcher.dispatchAction(createPayload('primary_click'))).toBe(true)
    expect(addCurrentWidgetToCell).toHaveBeenCalledWith(1)
    expect(closeShop).toHaveBeenCalledOnce()
  })

  it('uses pinch close/open for occupied-cell drag and drop', () => {
    const occupiedCells = ref(new Set([1]))
    const onWidgetMoved = vi.fn(({ sourceCellId, targetCellId }: { sourceCellId: number; targetCellId: number }) => {
      occupiedCells.value.delete(sourceCellId)
      occupiedCells.value.add(targetCellId)
    })

    const dispatcher = useActionDispatcher({
      isShopOpen: ref(false),
      openShop: vi.fn(),
      closeShop: vi.fn(),
      toggleShop: vi.fn(),
      isEditMode: ref(true),
      visibleCellIds: () => [1, 2, 3, 4],
      isCellAvailable: (cellId) => !occupiedCells.value.has(cellId),
      isCellOccupied: (cellId) => occupiedCells.value.has(cellId),
      moduleShopRef: ref(null),
      onWidgetMoved: (sourceCellId, targetCellId) => onWidgetMoved({ sourceCellId, targetCellId }),
    })

    expect(dispatcher.dispatchAction(createPayload('primary_click'))).toBe(true)
    expect(dispatcher.isDragging.value).toBe(true)
    expect(dispatcher.dragSourceCell.value).toBe(1)

    expect(dispatcher.dispatchAction(createPayload('move_focus_right'))).toBe(true)
    expect(dispatcher.focusedCellId.value).toBe(2)
    expect(dispatcher.dispatchAction(createPayload('drop_widget'))).toBe(true)

    expect(onWidgetMoved).toHaveBeenCalledWith({ sourceCellId: 1, targetCellId: 2 })
    expect(dispatcher.isDragging.value).toBe(false)
  })

  it('starts delete confirmation, cancels with circle, and auto-confirms otherwise', async () => {
    vi.useFakeTimers()
    const onWidgetDeleted = vi.fn()

    try {
      const dispatcher = useActionDispatcher({
        isShopOpen: ref(false),
        openShop: vi.fn(),
        closeShop: vi.fn(),
        toggleShop: vi.fn(),
        isEditMode: ref(true),
        visibleCellIds: () => [1, 2, 3, 4],
        isCellAvailable: () => false,
        isCellOccupied: (cellId) => cellId === 1,
        moduleShopRef: ref(null),
        onWidgetDeleted,
      })

      expect(dispatcher.dispatchAction(createPayload('delete_widget'))).toBe(true)
      await nextTick()
      expect(dispatcher.deleteConfirmCell.value).toBe(1)
      expect(dispatcher.dispatchAction(createPayload('toggle_edit_mode'))).toBe(true)
      await nextTick()
      expect(dispatcher.deleteConfirmCell.value).toBeNull()
      vi.advanceTimersByTime(2000)
      expect(onWidgetDeleted).not.toHaveBeenCalled()

      expect(dispatcher.dispatchAction(createPayload('delete_widget'))).toBe(true)
      await nextTick()
      vi.advanceTimersByTime(2000)
      expect(onWidgetDeleted).toHaveBeenCalledWith(1)
      expect(dispatcher.deleteConfirmCell.value).toBeNull()
    } finally {
      vi.useRealTimers()
    }
  })
})