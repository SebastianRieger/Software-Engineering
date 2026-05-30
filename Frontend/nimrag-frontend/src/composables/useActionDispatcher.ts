import { ref, watch, type Ref } from 'vue'

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
  isCellOccupied: (cellId: number) => boolean
  resizeCell?: (cellId: number, direction: ResizeDirection) => void
  moduleShopRef: Ref<ModuleShopControl | null>
  currentView?: Ref<'home' | 'grid'>
  navigateCamera?: (dir: 'up' | 'down') => void
  goToGrid?: () => void
  onWidgetMoved?: (sourceCellId: number, targetCellId: number) => void
  onWidgetDeleted?: (cellId: number) => void
}

const GRID_COLUMNS = 4
const GRID_ROWS = 4
const DELETE_CONFIRM_MS = 2000

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
  const isDragging = ref(false)
  const dragSourceCell = ref<number | null>(null)
  const deleteConfirmCell = ref<number | null>(null)

  let deleteTimer: ReturnType<typeof setTimeout> | null = null

  // Auto-confirm delete after 2 s; circle cancels it
  watch(deleteConfirmCell, (cell) => {
    if (deleteTimer !== null) {
      clearTimeout(deleteTimer)
      deleteTimer = null
    }
    if (cell !== null) {
      deleteTimer = setTimeout(() => {
        const toDelete = deleteConfirmCell.value
        if (toDelete !== null) {
          deleteConfirmCell.value = null
          options.onWidgetDeleted?.(toDelete)
          syncFocusedCell()
        }
      }, DELETE_CONFIRM_MS)
    }
  })

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
      const next = getNextCellId(candidate, direction)
      if (next === null) return false
      candidate = next
      if (visibleCellSet.has(candidate)) {
        focusedCellId.value = candidate
        return true
      }
    }
  }

  const focusGridCell = (cellId: number | null | undefined): boolean => {
    if (cellId == null) return false
    const visibleCells = options.visibleCellIds()
    if (!visibleCells.includes(cellId)) return false
    focusedCellId.value = cellId
    return true
  }

  const confirmFocusedSelection = (): boolean => {
    syncFocusedCell()
    if (!options.isShopOpen.value) return false
    if (!options.isCellAvailable(focusedCellId.value)) return false
    const shop = options.moduleShopRef.value
    if (!shop) return false
    shop.addCurrentWidgetToCell(focusedCellId.value)
    options.closeShop()
    return true
  }

  const dispatchAction = (payload: UIActionRequestedPayload): boolean => {
    switch (payload.action) {

      // ── Edit mode toggle (circle) ──────────────────────────────
      case 'toggle_edit_mode':
        if (options.isShopOpen.value) {
          options.closeShop()
        } else if (deleteConfirmCell.value !== null) {
          deleteConfirmCell.value = null
        } else if (isDragging.value) {
          isDragging.value = false
          dragSourceCell.value = null
        } else if (options.isEditMode.value) {
          options.setEditMode?.(false)
        } else {
          // Entering edit mode always switches to grid view first
          options.goToGrid?.()
          options.setEditMode?.(true)
        }
        return true

      // ── Pinch close: context-sensitive primary action ──────────
      case 'primary_click':
      case 'confirm_selection':
        // Shop open → confirm widget placement at current focused cell
        if (options.isShopOpen.value) {
          return confirmFocusedSelection()
        }
        // Dragging → drop at current focused cell (cursor position)
        if (options.isEditMode.value && isDragging.value) {
          const source = dragSourceCell.value
          const target = focusedCellId.value
          isDragging.value = false
          dragSourceCell.value = null
          if (source !== null && source !== target) {
            options.onWidgetMoved?.(source, target)
          }
          return true
        }
        // Edit mode + empty cell under cursor → open shop
        if (options.isEditMode.value && options.isCellAvailable(focusedCellId.value)) {
          options.openShop()
          return true
        }
        // Edit mode + occupied cell under cursor → begin drag
        if (options.isEditMode.value && options.isCellOccupied(focusedCellId.value)) {
          isDragging.value = true
          dragSourceCell.value = focusedCellId.value
          return true
        }
        return false

      // ── Pinch open: drop widget ────────────────────────────────
      case 'drop_widget':
        if (options.isEditMode.value && isDragging.value) {
          const source = dragSourceCell.value
          const target = focusedCellId.value
          isDragging.value = false
          dragSourceCell.value = null
          if (source !== null && source !== target) {
            options.onWidgetMoved?.(source, target)
          }
          return true
        }
        return false

      // ── Push short: resize (single push cycles size) ──────────
      case 'resize_expand':
        if (!options.resizeCell || !options.isEditMode.value) return false
        if (options.isCellOccupied(focusedCellId.value)) {
          options.resizeCell(focusedCellId.value, 'expand')
          syncFocusedCell()
          return true
        }
        return false

      case 'resize_shrink':
        if (!options.resizeCell || !options.isEditMode.value) return false
        if (options.isCellOccupied(focusedCellId.value)) {
          options.resizeCell(focusedCellId.value, 'shrink')
          syncFocusedCell()
          return true
        }
        return false

      // ── Push long: delete widget (with auto-confirm countdown) ─
      case 'delete_widget':
        if (
          options.isEditMode.value &&
          !isDragging.value &&
          deleteConfirmCell.value === null &&
          options.isCellOccupied(focusedCellId.value)
        ) {
          deleteConfirmCell.value = focusedCellId.value
          return true
        }
        return false

      // ── Navigation ─────────────────────────────────────────────
      // Home screen uses gestures for view/camera navigation; otherwise the
      // same actions move focus across the grid or module shop.
      case 'move_focus_left':
        if (options.isShopOpen.value && options.moduleShopRef.value) {
          options.moduleShopRef.value.prevModule()
          return true
        }
        if (!options.isEditMode.value && options.currentView?.value === 'home') {
          options.goToGrid?.()
          return true
        }
        return moveFocus('left')

      case 'move_focus_right':
        if (options.isShopOpen.value && options.moduleShopRef.value) {
          options.moduleShopRef.value.nextModule()
          return true
        }
        return moveFocus('right')

      case 'move_focus_up':
        if (!options.isEditMode.value && options.currentView?.value === 'home') {
          options.navigateCamera?.('up')
          return true
        }
        return moveFocus('up')

      case 'move_focus_down':
        if (!options.isEditMode.value && options.currentView?.value === 'home') {
          options.navigateCamera?.('down')
          return true
        }
        return moveFocus('down')

      case 'focus_grid_cell':
        return focusGridCell(payload.action_args.cell_index)

      // ── Shop (voice / legacy) ──────────────────────────────────
      case 'toggle_shop':
        options.toggleShop()
        return true

      case 'open_shop':
        options.openShop()
        return true

      case 'close_shop':
        options.closeShop()
        return true

      // ── Edit mode (voice / legacy keyboard) ───────────────────
      case 'enter_arrange_mode':
        options.setEditMode?.(true)
        return options.setEditMode !== undefined

      case 'exit_arrange_mode':
        options.setEditMode?.(false)
        return options.setEditMode !== undefined

      // ── Cancel ─────────────────────────────────────────────────
      case 'cancel_selection':
        if (isDragging.value) {
          isDragging.value = false
          dragSourceCell.value = null
        }
        deleteConfirmCell.value = null
        if (options.isShopOpen.value) options.closeShop()
        return true

      default:
        return false
    }
  }

  const handleRealtimeEvent = (event: RealtimeEvent): boolean => {
    if (event.eventType !== 'UIActionRequested') return false
    if (!isUIActionRequestedPayload(event.payload)) return false
    return dispatchAction(event.payload)
  }

  return {
    focusedCellId,
    isDragging,
    dragSourceCell,
    deleteConfirmCell,
    syncFocusedCell,
    dispatchAction,
    handleRealtimeEvent,
  }
}
