import { ref, computed, markRaw } from 'vue'
import type { Component } from 'vue'

const widgetMap = ref<Record<number, Component>>({})

export function useWidgetManager() {
  const occupiedCells = computed(() => Object.keys(widgetMap.value).map(Number))

  const insertWidgetIntoCell = (cellId: number, component: Component): void => {
    widgetMap.value = { ...widgetMap.value, [cellId]: markRaw(component) }
  }

  const moveWidgets = ({ sourceCellId, targetCellId }: { sourceCellId: number; targetCellId: number }): void => {
    const next = { ...widgetMap.value }
    const sourceComponent = next[sourceCellId]
    const targetComponent = next[targetCellId]

    if (sourceComponent !== undefined) next[targetCellId] = sourceComponent
    else delete next[targetCellId]

    if (targetComponent !== undefined) next[sourceCellId] = targetComponent
    else delete next[sourceCellId]

    widgetMap.value = next
  }

  const clearCell = (cellId: number): void => {
    const next = { ...widgetMap.value }
    delete next[cellId]
    widgetMap.value = next
  }

  return {
    widgetMap,
    insertWidgetIntoCell,
    moveWidgets,
    clearCell,
    occupiedCells,
  }
}
