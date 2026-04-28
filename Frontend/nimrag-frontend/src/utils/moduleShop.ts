import { listWidgetDefinitions, type WidgetDefinition } from '../widgets/registry'

export type ModuleItem = WidgetDefinition

export type DisplayItem = ModuleItem & {
  position: 'left' | 'center' | 'right'
  index: number
}

export const CELL_IDS = Array.from({ length: 16 }, (_, index) => index + 1)

export function getModuleItems(): ModuleItem[] {
  return listWidgetDefinitions()
}

export function moveModuleIndex(currentIndex: number, direction: 1 | -1, listLength: number): number {
  if (listLength === 0) {
    return 0
  }

  return (currentIndex + direction + listLength) % listLength
}

export function buildDisplayedModules(moduleList: ModuleItem[], currentIndex: number): DisplayItem[] {
  if (moduleList.length === 0) {
    return []
  }

  if (moduleList.length === 1) {
    const firstItem = moduleList[0]
    if (!firstItem) {
      return []
    }

    return [{ ...firstItem, position: 'center', index: 0 }]
  }

  const leftIndex = moveModuleIndex(currentIndex, -1, moduleList.length)
  const rightIndex = moveModuleIndex(currentIndex, 1, moduleList.length)
  const leftItem = moduleList[leftIndex]
  const centerItem = moduleList[currentIndex]
  const rightItem = moduleList[rightIndex]

  if (!leftItem || !centerItem || !rightItem) {
    return []
  }

  return [
    { ...leftItem, position: 'left', index: leftIndex },
    { ...centerItem, position: 'center', index: currentIndex },
    { ...rightItem, position: 'right', index: rightIndex },
  ]
}