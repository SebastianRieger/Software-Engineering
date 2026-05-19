import { describe, it, expect } from 'vitest'
import { useWidgetResize } from '@/composables/useWidgetResize'

// cellSizes is a module-level singleton; use IDs >= 200 to avoid overlap
// with getVisibleCells (which iterates 1–16).
let nextId = 200
const uid = () => nextId++

describe('useWidgetResize', () => {
  describe('initializeCell', () => {
    it('sets default size 1 for a new cell', () => {
      const { initializeCell, cellSizes } = useWidgetResize()
      const id = uid()
      initializeCell(id)
      expect(cellSizes.value[id]).toBe(1)
    })

    it('does not overwrite an existing size (idempotent)', () => {
      const { initializeCell, cycleCellSize, cellSizes } = useWidgetResize()
      const id = uid()
      initializeCell(id)
      cycleCellSize(id) // 1 → 2
      initializeCell(id) // must be a no-op
      expect(cellSizes.value[id]).toBe(2)
    })
  })

  describe('cycleCellSize', () => {
    it('cycles 1 → 2 → 4 → 1', () => {
      const { initializeCell, cycleCellSize, cellSizes } = useWidgetResize()
      const id = uid()
      initializeCell(id)
      expect(cycleCellSize(id)).toBe(2)
      expect(cellSizes.value[id]).toBe(2)
      expect(cycleCellSize(id)).toBe(4)
      expect(cellSizes.value[id]).toBe(4)
      expect(cycleCellSize(id)).toBe(1)
      expect(cellSizes.value[id]).toBe(1)
    })

    it('treats uninitialized cell as size 1 before cycling', () => {
      const { cycleCellSize } = useWidgetResize()
      const id = uid()
      expect(cycleCellSize(id)).toBe(2)
    })
  })

  describe('getGridClass', () => {
    it('returns "" for size 1', () => {
      const { initializeCell, getGridClass } = useWidgetResize()
      const id = uid()
      initializeCell(id)
      expect(getGridClass(id)).toBe('')
    })

    it('returns "col-span-2" for size 2', () => {
      const { initializeCell, cycleCellSize, getGridClass } = useWidgetResize()
      const id = uid()
      initializeCell(id)
      cycleCellSize(id) // → 2
      expect(getGridClass(id)).toBe('col-span-2')
    })

    it('returns "col-span-2 row-span-2" for size 4', () => {
      const { initializeCell, cycleCellSize, getGridClass } = useWidgetResize()
      const id = uid()
      initializeCell(id)
      cycleCellSize(id) // → 2
      cycleCellSize(id) // → 4
      expect(getGridClass(id)).toBe('col-span-2 row-span-2')
    })

    it('returns "" for an unknown cell (defaults to 1)', () => {
      const { getGridClass } = useWidgetResize()
      expect(getGridClass(uid())).toBe('')
    })
  })

  describe('getSizeLabel', () => {
    it('returns "1×1" for size 1', () => {
      const { initializeCell, getSizeLabel } = useWidgetResize()
      const id = uid()
      initializeCell(id)
      expect(getSizeLabel(id)).toBe('1×1')
    })

    it('returns "2×1" for size 2', () => {
      const { initializeCell, cycleCellSize, getSizeLabel } = useWidgetResize()
      const id = uid()
      initializeCell(id)
      cycleCellSize(id)
      expect(getSizeLabel(id)).toBe('2×1')
    })

    it('returns "2×2" for size 4', () => {
      const { initializeCell, cycleCellSize, getSizeLabel } = useWidgetResize()
      const id = uid()
      initializeCell(id)
      cycleCellSize(id)
      cycleCellSize(id)
      expect(getSizeLabel(id)).toBe('2×2')
    })

    it('returns "1×1" for an unknown cell (defaults to 1)', () => {
      const { getSizeLabel } = useWidgetResize()
      expect(getSizeLabel(uid())).toBe('1×1')
    })
  })

  describe('getVisibleCells', () => {
    it('returns all 16 cells when every cell has size 1', () => {
      const { getVisibleCells, cellSizes } = useWidgetResize()
      for (let i = 1; i <= 16; i++) cellSizes.value[i] = 1
      const visible = getVisibleCells()
      expect(visible).toHaveLength(16)
      expect(visible[0]).toBe(1)
      expect(visible[15]).toBe(16)
    })

    it('reduces visible count when a cell is enlarged (size 4)', () => {
      const { getVisibleCells, cellSizes } = useWidgetResize()
      for (let i = 1; i <= 16; i++) cellSizes.value[i] = 1
      cellSizes.value[1] = 4 // 4 slots instead of 1 → 3 fewer trailing cells
      // used: 4 (cell1) + 12×1 (cells 2–13) = 16; cell 14 would exceed
      expect(getVisibleCells()).toHaveLength(13)
    })

    it('stops before a cell that exceeds remaining slots', () => {
      const { getVisibleCells, cellSizes } = useWidgetResize()
      for (let i = 1; i <= 16; i++) cellSizes.value[i] = 1
      // cell 16 needs 4 slots but only 1 remains after cells 1–15
      cellSizes.value[16] = 4
      const visible = getVisibleCells()
      expect(visible).toHaveLength(15)
      expect(visible).not.toContain(16)
      // Cleanup
      cellSizes.value[16] = 1
    })

    it('returns first cell only when it consumes all 16 slots', () => {
      const { getVisibleCells, cellSizes } = useWidgetResize()
      for (let i = 1; i <= 16; i++) cellSizes.value[i] = 1
      cellSizes.value[1] = 4
      cellSizes.value[2] = 4
      cellSizes.value[3] = 4
      cellSizes.value[4] = 4
      // 4×4 = 16, so only cells 1–4 are visible
      const visible = getVisibleCells()
      expect(visible).toHaveLength(4)
      // Cleanup
      for (let i = 1; i <= 4; i++) cellSizes.value[i] = 1
    })
  })
})
