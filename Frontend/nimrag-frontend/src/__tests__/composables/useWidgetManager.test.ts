import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { useWidgetManager } from '@/composables/useWidgetManager'

const SimpleWidget = defineComponent({
  name: 'SimpleWidget',
  render() { return h('div', { class: 'simple-widget' }, 'Widget') },
})

const OtherWidget = defineComponent({
  name: 'OtherWidget',
  render() { return h('div', { class: 'other-widget' }, 'Other') },
})

beforeEach(() => {
  // Clear localStorage so no persisted state bleeds between tests
  localStorage.clear()
  const { widgetMap } = useWidgetManager()
  widgetMap.value = {}
})

describe('useWidgetManager', () => {
  describe('insertWidgetIntoCell', () => {
    it('adds the component to widgetMap and marks the cell as occupied', () => {
      const { insertWidgetIntoCell, widgetMap, occupiedCells } = useWidgetManager()

      insertWidgetIntoCell(1, SimpleWidget)
      expect(widgetMap.value[1]).toBe(SimpleWidget)
      expect(occupiedCells.value).toContain(1)
    })

    it('replaces an existing widget when called twice on the same cell', () => {
      const { insertWidgetIntoCell, widgetMap, occupiedCells } = useWidgetManager()

      insertWidgetIntoCell(1, SimpleWidget)
      insertWidgetIntoCell(1, OtherWidget)
      expect(widgetMap.value[1]).toBe(OtherWidget)
      expect(occupiedCells.value.filter((c: number) => c === 1)).toHaveLength(1)
    })
  })

  describe('clearCell', () => {
    it('removes the component from widgetMap and the cell from occupiedCells', () => {
      const { insertWidgetIntoCell, clearCell, widgetMap, occupiedCells } = useWidgetManager()

      insertWidgetIntoCell(1, SimpleWidget)
      expect(occupiedCells.value).toContain(1)

      clearCell(1)
      expect(widgetMap.value[1]).toBeUndefined()
      expect(occupiedCells.value).not.toContain(1)
    })

    it('does not throw when called on an empty cell', () => {
      const { clearCell } = useWidgetManager()
      expect(() => clearCell(99)).not.toThrow()
    })
  })

  describe('moveWidgets', () => {
    it('swaps two occupied cells in widgetMap', () => {
      const { insertWidgetIntoCell, moveWidgets, widgetMap, occupiedCells } = useWidgetManager()

      insertWidgetIntoCell(1, SimpleWidget)
      insertWidgetIntoCell(2, OtherWidget)

      moveWidgets({ sourceCellId: 1, targetCellId: 2 })

      expect(widgetMap.value[1]).toBe(OtherWidget)
      expect(widgetMap.value[2]).toBe(SimpleWidget)
      expect(occupiedCells.value).toContain(1)
      expect(occupiedCells.value).toContain(2)
    })

    it('moves source widget to an empty target cell', () => {
      const { insertWidgetIntoCell, moveWidgets, widgetMap, occupiedCells } = useWidgetManager()

      insertWidgetIntoCell(1, SimpleWidget)
      moveWidgets({ sourceCellId: 1, targetCellId: 2 })

      expect(widgetMap.value[1]).toBeUndefined()
      expect(widgetMap.value[2]).toBe(SimpleWidget)
      expect(occupiedCells.value).not.toContain(1)
      expect(occupiedCells.value).toContain(2)
    })

    it('moves target widget to an empty source cell', () => {
      const { insertWidgetIntoCell, moveWidgets, widgetMap, occupiedCells } = useWidgetManager()

      insertWidgetIntoCell(2, SimpleWidget)
      moveWidgets({ sourceCellId: 1, targetCellId: 2 })

      expect(widgetMap.value[1]).toBe(SimpleWidget)
      expect(widgetMap.value[2]).toBeUndefined()
      expect(occupiedCells.value).toContain(1)
      expect(occupiedCells.value).not.toContain(2)
    })

    it('does nothing when both cells are empty', () => {
      const { moveWidgets, widgetMap } = useWidgetManager()
      expect(() => moveWidgets({ sourceCellId: 1, targetCellId: 2 })).not.toThrow()
      expect(widgetMap.value[1]).toBeUndefined()
      expect(widgetMap.value[2]).toBeUndefined()
    })
  })

  // ── localStorage integration ────────────────────────────────────────────

  describe('loadFromStorage', () => {
    afterEach(() => {
      localStorage.clear()
      vi.resetModules()
    })

    it('loads a known widget from localStorage on module initialization', async () => {
      localStorage.setItem('nimrag-widget-map', JSON.stringify({ '3': 'ClockWidget' }))

      vi.resetModules()
      const { useWidgetManager: freshUseWidgetManager } = await import('@/composables/useWidgetManager')
      const { widgetMap } = freshUseWidgetManager()

      // ClockWidget is registered – should be loaded
      expect(widgetMap.value[3]).toBeDefined()
    })

    it('starts with an empty layout when no saved layout exists', async () => {
      localStorage.removeItem('nimrag-widget-map')
      vi.resetModules()
      const { useWidgetManager: freshUseWidgetManager } = await import('@/composables/useWidgetManager')
      const { widgetMap } = freshUseWidgetManager()

      expect(widgetMap.value).toEqual({})
    })

    it('silently skips unknown widget names from localStorage', async () => {
      localStorage.setItem('nimrag-widget-map', JSON.stringify({ '4': 'UnknownWidgetXYZ' }))

      vi.resetModules()
      const { useWidgetManager: freshUseWidgetManager } = await import('@/composables/useWidgetManager')
      const { widgetMap } = freshUseWidgetManager()

      expect(widgetMap.value[4]).toBeUndefined()
    })

    it('returns empty map when localStorage contains invalid JSON', async () => {
      localStorage.setItem('nimrag-widget-map', 'this-is-not-valid-json')

      vi.resetModules()
      const { useWidgetManager: freshUseWidgetManager } = await import('@/composables/useWidgetManager')
      const { widgetMap } = freshUseWidgetManager()

      expect(widgetMap.value).toEqual({})
    })
  })
})
