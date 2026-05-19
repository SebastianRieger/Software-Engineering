import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { useWidgetManager } from '@/composables/useWidgetManager'

// Minimal widget component that renders a recognisable div
const SimpleWidget = defineComponent({
  name: 'SimpleWidget',
  render() {
    return h('div', { class: 'simple-widget' }, 'Widget')
  },
})

// mountedApps and occupiedCells are module-level singletons.
// Use a high base ID to avoid collisions across tests in this file.
let nextId = 500
const uid = () => nextId++

// Helpers to set up / tear down DOM mount-points
function createMount(cellId: number): HTMLElement {
  const el = document.createElement('div')
  el.id = `cell-content-${cellId}`
  document.body.appendChild(el)
  return el
}

afterEach(() => {
  document.body.innerHTML = ''
})

describe('useWidgetManager', () => {
  describe('insertWidgetIntoCell', () => {
    it('mounts the component and marks the cell as occupied', () => {
      const id = uid()
      createMount(id)
      const { insertWidgetIntoCell, occupiedCells } = useWidgetManager()

      insertWidgetIntoCell(id, SimpleWidget)
      expect(occupiedCells.value).toContain(id)
    })

    it('renders widget content into the mount element', () => {
      const id = uid()
      const el = createMount(id)
      const { insertWidgetIntoCell } = useWidgetManager()

      insertWidgetIntoCell(id, SimpleWidget)
      expect(el.querySelector('.simple-widget')).not.toBeNull()
    })

    it('replaces an existing widget when called twice on the same cell', () => {
      const id = uid()
      createMount(id)
      const { insertWidgetIntoCell, occupiedCells } = useWidgetManager()

      insertWidgetIntoCell(id, SimpleWidget)
      insertWidgetIntoCell(id, SimpleWidget)
      // Still one occurrence in occupiedCells
      expect(occupiedCells.value.filter(c => c === id)).toHaveLength(1)
    })

    it('does nothing when the mount element does not exist', () => {
      const { insertWidgetIntoCell, occupiedCells } = useWidgetManager()
      const id = uid()

      expect(() => insertWidgetIntoCell(id, SimpleWidget)).not.toThrow()
      expect(occupiedCells.value).not.toContain(id)
    })
  })

  describe('clearCell', () => {
    it('unmounts the widget and removes the cell from occupiedCells', () => {
      const id = uid()
      createMount(id)
      const { insertWidgetIntoCell, clearCell, occupiedCells } = useWidgetManager()

      insertWidgetIntoCell(id, SimpleWidget)
      expect(occupiedCells.value).toContain(id)

      clearCell(id)
      expect(occupiedCells.value).not.toContain(id)
    })

    it('restores a placeholder element in the mount point', () => {
      const id = uid()
      const el = createMount(id)
      const { insertWidgetIntoCell, clearCell } = useWidgetManager()

      insertWidgetIntoCell(id, SimpleWidget)
      clearCell(id)

      // _restorePlaceholder creates a div with opacity-70 class
      expect(el.querySelector('.opacity-70')).not.toBeNull()
      expect(el.querySelector('.opacity-70')!.textContent).toBe(
        String(id).padStart(2, '0')
      )
    })

    it('does not throw when called on an empty cell', () => {
      const id = uid()
      createMount(id)
      const { clearCell } = useWidgetManager()

      expect(() => clearCell(id)).not.toThrow()
    })

    it('does not throw when the mount element does not exist', () => {
      const { clearCell } = useWidgetManager()
      expect(() => clearCell(uid())).not.toThrow()
    })
  })

  describe('moveWidgets', () => {
    it('swaps two widgets between cells', () => {
      const srcId = uid()
      const tgtId = uid()
      const srcEl = createMount(srcId)
      const tgtEl = createMount(tgtId)

      const { insertWidgetIntoCell, moveWidgets, occupiedCells } = useWidgetManager()
      insertWidgetIntoCell(srcId, SimpleWidget)
      insertWidgetIntoCell(tgtId, SimpleWidget)

      const srcChild = srcEl.firstElementChild
      const tgtChild = tgtEl.firstElementChild

      moveWidgets({ sourceCellId: srcId, targetCellId: tgtId })

      // After swap DOM nodes crossed over
      expect(srcEl.firstElementChild).toBe(tgtChild)
      expect(tgtEl.firstElementChild).toBe(srcChild)

      // Both cells still occupied (apps swapped in the map)
      expect(occupiedCells.value).toContain(srcId)
      expect(occupiedCells.value).toContain(tgtId)
    })

    it('moves source widget to empty target cell', () => {
      const srcId = uid()
      const tgtId = uid()
      createMount(srcId)
      createMount(tgtId) // empty – no children

      const { insertWidgetIntoCell, moveWidgets, occupiedCells } = useWidgetManager()
      insertWidgetIntoCell(srcId, SimpleWidget)

      moveWidgets({ sourceCellId: srcId, targetCellId: tgtId })

      const srcEl = document.getElementById(`cell-content-${srcId}`)!
      const tgtEl = document.getElementById(`cell-content-${tgtId}`)!

      expect(srcEl.firstElementChild).toBeNull()
      expect(tgtEl.firstElementChild).not.toBeNull()
      expect(occupiedCells.value).not.toContain(srcId)
      expect(occupiedCells.value).toContain(tgtId)
    })

    it('moves target widget to empty source cell', () => {
      const srcId = uid()
      const tgtId = uid()
      createMount(srcId) // empty
      createMount(tgtId)

      const { insertWidgetIntoCell, moveWidgets, occupiedCells } = useWidgetManager()
      insertWidgetIntoCell(tgtId, SimpleWidget)

      moveWidgets({ sourceCellId: srcId, targetCellId: tgtId })

      const srcEl = document.getElementById(`cell-content-${srcId}`)!
      const tgtEl = document.getElementById(`cell-content-${tgtId}`)!

      expect(srcEl.firstElementChild).not.toBeNull()
      expect(tgtEl.firstElementChild).toBeNull()
    })

    it('does nothing when both cells are empty', () => {
      const srcId = uid()
      const tgtId = uid()
      createMount(srcId)
      createMount(tgtId)

      const { moveWidgets } = useWidgetManager()
      expect(() => moveWidgets({ sourceCellId: srcId, targetCellId: tgtId })).not.toThrow()
    })

    it('does nothing when mount elements do not exist', () => {
      const { moveWidgets } = useWidgetManager()
      expect(() =>
        moveWidgets({ sourceCellId: uid(), targetCellId: uid() })
      ).not.toThrow()
    })
  })
})
