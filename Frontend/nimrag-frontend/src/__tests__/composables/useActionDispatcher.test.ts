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
})