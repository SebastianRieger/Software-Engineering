import { ref } from 'vue';

export type CellSize = 1 | 2 | 4;

/**
 * Composable für Widget-Größenänderungen
 * Verantwortung: Verwaltung der Grid-Größen pro Widget-Zelle
 * 1 = 1x1, 2 = 2x1, 4 = 2x2
 */
export function useWidgetResize() {
  const cellSizes = ref<{ [key: number]: CellSize }>({});

  /**
   * Initialisiert eine Zelle mit Default-Größe 1x1
   */
  const initializeCell = (cellId: number) => {
    if (!(cellId in cellSizes.value)) {
      cellSizes.value[cellId] = 1;
    }
  };

  /**
   * Cycled durch verfügbare Größen: 1x1 → 2x1 → 2x2 → 1x1
   */
  const cycleCellSize = (cellId: number): CellSize => {
    const currentSize = cellSizes.value[cellId] || 1;

    const sizeSequence: CellSize[] = [1, 2, 4];
    const currentIndex = sizeSequence.indexOf(currentSize as CellSize);
    const nextIndex = (currentIndex + 1) % sizeSequence.length;

    const newSize: CellSize = sizeSequence[nextIndex]!;
    cellSizes.value[cellId] = newSize;

    return newSize;
  };

  /**
   * Gibt CSS-Klassen für Grid-Spanning zurück
   */
  const getGridClass = (cellId: number): string => {
    const size = cellSizes.value[cellId] || 1;

    switch (size) {
      case 2:
        return 'col-span-2'; // 2x1
      case 4:
        return 'col-span-2 row-span-2'; // 2x2
      case 1:
      default:
        return '';
    }
  };

  /**
   * Gibt lesbare Größen-Label zurück
   */
  const getSizeLabel = (cellId: number): string => {
    const size = cellSizes.value[cellId] || 1;
    switch (size) {
      case 2:
        return '2x1';
      case 4:
        return '2x2';
      case 1:
      default:
        return '1x1';
    }
  };

  /**
   * Berechnet, welche Zellen in das 4×4 Grid passen
   * Zellen, die nicht passen, werden gefiltert
   */
  const getVisibleCells = (): number[] => {
    const maxGridSize = 16; // 4x4 = 16 Plätze
    const visibleCells: number[] = [];
    let totalSize = 0;

    for (let i = 1; i <= 16; i++) {
      const cellSize = cellSizes.value[i] || 1;

      if (totalSize + cellSize <= maxGridSize) {
        visibleCells.push(i);
        totalSize += cellSize;
      }
    }

    return visibleCells;
  };

  return {
    cellSizes,
    initializeCell,
    cycleCellSize,
    getGridClass,
    getSizeLabel,
    getVisibleCells,
  };
}


