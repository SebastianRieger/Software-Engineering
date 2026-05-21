import { ref } from 'vue'

export type CellSize = 1 | 2 | 4

// Singleton outside the function → shared across all instances and
// createApp() widgets via provide/inject
const cellSizes = ref<Record<number, CellSize>>({})

/**
 * Composable for widget size management.
 * Responsible for tracking and cycling grid sizes per cell.
 *   1 = 1×1  |  2 = 2×1  |  4 = 2×2
 */
export function useWidgetResize() {
  const sequence: CellSize[] = [1, 2, 4]

  /**
   * Initializes a cell with default size 1×1 (idempotent).
   */
  const initializeCell = (cellId: number): void => {
    if (!(cellId in cellSizes.value)) {
      cellSizes.value[cellId] = 1
    }
  }

  /**
   * Cycles through available sizes: 1×1 → 2×1 → 2×2 → 1×1
   */
  const cycleCellSize = (cellId: number): CellSize => {
    const current = cellSizes.value[cellId] ?? 1
    const next = sequence[(sequence.indexOf(current) + 1) % sequence.length]!
    cellSizes.value[cellId] = next
    return next
  }

  /**
   * Resizes a cell in an explicit direction without cycling past the bounds.
   */
  const resizeCell = (cellId: number, direction: 'expand' | 'shrink'): CellSize => {
    const current = cellSizes.value[cellId] ?? 1
    const currentIndex = sequence.indexOf(current)
    const nextIndex = direction === 'expand'
      ? Math.min(currentIndex + 1, sequence.length - 1)
      : Math.max(currentIndex - 1, 0)
    const next = sequence[nextIndex]!
    cellSizes.value[cellId] = next
    return next
  }

  /**
   * Returns Tailwind grid-span classes for a given cell.
   */
  const getGridClass = (cellId: number): string => {
    switch (cellSizes.value[cellId] ?? 1) {
      case 2:  return 'col-span-2'
      case 4:  return 'col-span-2 row-span-2'
      default: return ''
    }
  }

  /**
   * Returns a human-readable size label (used for resize button tooltip).
   */
  const getSizeLabel = (cellId: number): string => {
    switch (cellSizes.value[cellId] ?? 1) {
      case 2:  return '2×1'
      case 4:  return '2×2'
      default: return '1×1'
    }
  }

  /**
   * Calculates which cells fit into the 4×4 grid.
   * Cells are accumulated in order until all 16 slots are filled.
   */
  const getVisibleCells = (): number[] => {
    const visible: number[] = []
    let used = 0

    for (let i = 1; i <= 16; i++) {
      const size = cellSizes.value[i] ?? 1
      if (used + size > 16) break
      visible.push(i)
      used += size
    }

    return visible
  }

  return {
    cellSizes,   // Exposed directly so it can be passed via provide
    initializeCell,
    cycleCellSize,
    resizeCell,
    getGridClass,
    getSizeLabel,
    getVisibleCells,
  }
}