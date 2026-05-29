import { ref, type Ref } from 'vue'

import type { UIActionRequestedPayload } from '../types/interactions'
import type { RealtimeEvent } from '../types/realtime'

type FocusDirection = 'left' | 'right' | 'up' | 'down'
type ResizeDirection = 'expand' | 'shrink'

interface ModuleShopControl {
  nextModule: () => void
  prevModule: () => void
  addCurrentWidgetToCell: (cellId: number) => void
}

interface ActionDispatcherOptions {
  isShopOpen: Ref<boolean>
  openShop: () => void
  closeShop: () => void
  toggleShop: () => void
  isEditMode: Ref<boolean>
  setEditMode?: (value: boolean) => void
  visibleCellIds: () => number[]
  isCellAvailable: (cellId: number) => boolean
  resizeCell?: (cellId: number, direction: ResizeDirection) => void
  moduleShopRef: Ref<ModuleShopControl | null>
  currentView?: Ref<'home' | 'grid'>
  navigateCamera?: (dir: 'up' | 'down') => void
  goToGrid?: () => void
}

const GRID_COLUMNS = 4
const GRID_ROWS = 4

function getNextCellId(cellId: number, direction: FocusDirection): number | null {
  switch (direction) {
    case 'left':
      return cellId % GRID_COLUMNS === 1 ? null : cellId - 1
    case 'right':
      return cellId % GRID_COLUMNS === 0 ? null : cellId + 1
    case 'up':
      return cellId <= GRID_COLUMNS ? null : cellId - GRID_COLUMNS
    case 'down':
      return cellId > GRID_COLUMNS * (GRID_ROWS - 1) ? null : cellId + GRID_COLUMNS
  }
}

function isUIActionRequestedPayload(payload: RealtimeEvent['payload']): payload is UIActionRequestedPayload {
  return payload !== null && typeof payload === 'object' && 'action' in payload
}

export function useActionDispatcher(options: ActionDispatcherOptions) {
  const focusedCellId = ref(1)

  const syncFocusedCell = (): void => {
    const visibleCells = options.visibleCellIds()
    if (visibleCells.length === 0) {
      focusedCellId.value = 1
      return
    }

    if (!visibleCells.includes(focusedCellId.value)) {
      focusedCellId.value = visibleCells[0]!
    }
  }

  const moveFocus = (direction: FocusDirection): boolean => {
    syncFocusedCell()
    const visibleCellSet = new Set(options.visibleCellIds())
    let candidate = focusedCellId.value

    while (true) {
      const nextCandidate = getNextCellId(candidate, direction)
      if (nextCandidate === null) {
        return false
      }

      candidate = nextCandidate
      if (visibleCellSet.has(candidate)) {
        focusedCellId.value = candidate
        return true
      }
    }
  }

  const focusGridCell = (cellId: number | null | undefined): boolean => {
    if (cellId == null) {
      return false
    }

    const visibleCells = options.visibleCellIds()
    if (!visibleCells.includes(cellId)) {
      return false
    }

    focusedCellId.value = cellId
    return true
  }

  const confirmFocusedSelection = (): boolean => {
    syncFocusedCell()

    if (!options.isShopOpen.value) {
      return false
    }

    if (!options.isCellAvailable(focusedCellId.value)) {
      return false
    }

    const moduleShop = options.moduleShopRef.value
    if (!moduleShop) {
      return false
    }

    moduleShop.addCurrentWidgetToCell(focusedCellId.value)
    options.closeShop()
    return true
  }

  const dispatchAction = (payload: UIActionRequestedPayload): boolean => {
    switch (payload.action) {
      case 'move_focus_left':
        if (options.isShopOpen.value && options.moduleShopRef.value) {
          options.moduleShopRef.value.prevModule()
          return true
        }
        return moveFocus('left')

      case 'move_focus_right':
        if (options.currentView?.value === 'home') {
          options.goToGrid?.()
          return true
        }
        if (options.isShopOpen.value && options.moduleShopRef.value) {
          options.moduleShopRef.value.nextModule()
          return true
        }
        return moveFocus('right')

      case 'move_focus_up':
        if (options.currentView?.value === 'home') {
          options.navigateCamera?.('up')
          return true
        }
        return moveFocus('up')

      case 'move_focus_down':
        if (options.currentView?.value === 'home') {
          options.navigateCamera?.('down')
          return true
        }
        return moveFocus('down')

      case 'focus_grid_cell':
        return focusGridCell(payload.action_args.cell_index)

      case 'toggle_shop':
        options.toggleShop()
        return true

      case 'open_shop':
        options.openShop()
        return true

      case 'close_shop':
        options.closeShop()
        return true

      case 'primary_click':
      case 'confirm_selection':
        return confirmFocusedSelection()

      case 'enter_arrange_mode':
        options.setEditMode?.(true)
        return options.setEditMode !== undefined

      case 'exit_arrange_mode':
        options.setEditMode?.(false)
        return options.setEditMode !== undefined

      case 'resize_expand':
        if (!options.resizeCell) {
          return false
        }
        options.resizeCell(focusedCellId.value, 'expand')
        syncFocusedCell()
        return true

      case 'resize_shrink':
        if (!options.resizeCell) {
          return false
        }
        options.resizeCell(focusedCellId.value, 'shrink')
        syncFocusedCell()
        return true

      default:
        return false
    }
  }

  const handleRealtimeEvent = (event: RealtimeEvent): boolean => {
    if (event.eventType !== 'UIActionRequested') {
      return false
    }

    if (!isUIActionRequestedPayload(event.payload)) {
      return false
    }

    return dispatchAction(event.payload)
  }

  return {
    focusedCellId,
    syncFocusedCell,
    dispatchAction,
    handleRealtimeEvent,
  }
}