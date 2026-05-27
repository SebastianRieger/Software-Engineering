import { ref, computed, markRaw, watch } from 'vue'
import type { Component } from 'vue'
import CameraWidget from '../components/widgets/CameraWidget.vue'
import { getWidgetComponent, getWidgetName } from './widgetRegistry'

const STORAGE_KEY = 'nimrag-widget-map'

/**
 * Reads the widget map from localStorage.
 * Stored format: { "cellId": "WidgetName", ... }
 * Unknown widget names (e.g. removed widgets) are silently skipped.
 */
function loadFromStorage(): Record<number, Component> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { 1: markRaw(CameraWidget) }

    const saved = JSON.parse(raw) as Record<string, string>
    const result: Record<number, Component> = {}

    for (const [cellId, name] of Object.entries(saved)) {
      const component = getWidgetComponent(name)
      if (component) result[Number(cellId)] = markRaw(component)
    }

    return result
  } catch {
    return {}
  }
}

/**
 * Serializes the widget map to localStorage.
 * Components not found in the registry (e.g. test mocks) are silently omitted.
 */
function saveToStorage(map: Record<number, Component>): void {
  try {
    const toSave: Record<number, string> = {}

    for (const [cellId, component] of Object.entries(map)) {
      const name = getWidgetName(component as Component)
      if (name) toSave[Number(cellId)] = name
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
  } catch {
    // Silently fail if localStorage is unavailable (e.g. private mode restrictions)
  }
}

// Module-level singleton – shared across all composable instances.
// Initialized once from localStorage on first import.
const widgetMap = ref<Record<number, Component>>(loadFromStorage())

// Auto-persist on every change
watch(widgetMap, (map) => saveToStorage(map), { deep: true })

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
