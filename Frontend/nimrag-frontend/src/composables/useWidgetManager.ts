import { createApp } from 'vue'
import { useWidgetResize } from './useWidgetResize'

const { cellSizes } = useWidgetResize()

// Tracks all running app instances per cell for clean unmounting
const mountedApps = new Map<number, ReturnType<typeof createApp>>()

/**
 * Composable for widget lifecycle management.
 * Responsible for mounting, moving, and removing Vue app instances
 * inside grid cells.
 *
 * Each widget receives via provide:
 *   - cellId    → number
 *   - cellSizes → Ref<Record<number, CellSize>>  (reactive singleton)
 *
 * Widgets can then inject their current size like so:
 *   const cellId    = inject<number>('cellId', 0)
 *   const cellSizes = inject<Ref<Record<number, CellSize>>>('cellSizes', ref({}))
 *   const size = computed(() => {
 *     switch (cellSizes.value[cellId]) {
 *       case 4:  return 'large'
 *       case 2:  return 'medium'
 *       default: return 'small'
 *     }
 *   })
 */
export function useWidgetManager() {

  /**
   * Mounts a component into a grid cell.
   * Any existing app in that cell is cleanly unmounted first.
   */
  const insertWidgetIntoCell = (cellId: number, component: any): void => {
    const mount = document.getElementById(`cell-content-${cellId}`)
    if (!mount) return

    // Clean up existing instance before remounting
    _unmountCell(cellId)
    mount.innerHTML = ''

    const app = createApp(component)

    // Provide size context to the widget
    app.provide('cellId', cellId)
    app.provide('cellSizes', cellSizes) // pass the ref, not .value — keeps reactivity

    app.mount(mount)
    mountedApps.set(cellId, app)
  }

  /**
   * Swaps two widgets via DOM node replacement.
   * Vue app instances stay attached to their container divs —
   * only the DOM nodes are moved (no innerHTML copying).
   *
   * Note: cellId provides remain tied to their original app instance.
   * If exact cellId accuracy is required after a swap, remount via
   * insertWidgetIntoCell() instead.
   */
  const moveWidgets = ({
                         sourceCellId,
                         targetCellId,
                       }: {
    sourceCellId: number
    targetCellId: number
  }): void => {
    const sourceMount = document.getElementById(`cell-content-${sourceCellId}`)
    const targetMount = document.getElementById(`cell-content-${targetCellId}`)
    if (!sourceMount || !targetMount) return

    const sourceChild = sourceMount.firstElementChild
    const targetChild = targetMount.firstElementChild

    if (sourceChild && targetChild) {
      // Comment anchor prevents replaceChild from overwriting itself
      const anchor = document.createComment('swap')
      targetMount.replaceChild(anchor, targetChild)
      sourceMount.replaceChild(targetChild, sourceChild)
      targetMount.replaceChild(sourceChild, anchor)
    } else if (sourceChild) {
      targetMount.appendChild(sourceChild)
    } else if (targetChild) {
      sourceMount.appendChild(targetChild)
    }

    // Keep mountedApps map in sync after the swap
    const sourceApp = mountedApps.get(sourceCellId)
    const targetApp = mountedApps.get(targetCellId)
    if (sourceApp) mountedApps.set(targetCellId, sourceApp)
    else            mountedApps.delete(targetCellId)
    if (targetApp)  mountedApps.set(sourceCellId, targetApp)
    else            mountedApps.delete(sourceCellId)
  }

  /**
   * Unmounts the app in a cell and restores the empty placeholder.
   */
  const clearCell = (cellId: number): void => {
    _unmountCell(cellId)
    _restorePlaceholder(cellId)
  }

  // ── Private helpers ───────────────────────────────────────────────────────

  function _unmountCell(cellId: number): void {
    const app = mountedApps.get(cellId)
    if (app) {
      app.unmount()
      mountedApps.delete(cellId)
    }
  }

  function _restorePlaceholder(cellId: number): void {
    const mount = document.getElementById(`cell-content-${cellId}`)
    if (!mount) return

    mount.innerHTML = ''
    const placeholder = document.createElement('div')
    placeholder.className = 'w-full h-full grid place-items-center text-2xl font-semibold opacity-70'
    placeholder.textContent = String(cellId).padStart(2, '0')
    mount.appendChild(placeholder)
  }

  return {
    insertWidgetIntoCell,
    moveWidgets,
    clearCell,
  }
}