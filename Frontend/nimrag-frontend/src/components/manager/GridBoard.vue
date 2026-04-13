<script setup lang="ts">
import type { Component } from 'vue'

import type { WidgetConfig } from '../../types/config'

interface RenderedWidget extends WidgetConfig {
  component: Component | null
  widgetProps?: Record<string, unknown>
}

defineProps<{
  widgets: Record<number, RenderedWidget | undefined>
}>()

const emit = defineEmits<{
  moveWidget: [payload: { sourceCellId: number; targetCellId: number }]
}>()

function onDragStart(event: DragEvent, cellId: number, hasWidget: boolean) {
  if (!hasWidget) {
    event.preventDefault()
    return
  }

  const cell = event.currentTarget as HTMLElement | null
  if (!cell) return

  event.dataTransfer?.setData('text/plain', String(cellId))
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }

  const ghost = document.createElement('div')
  ghost.style.width = '1px'
  ghost.style.height = '1px'
  ghost.style.opacity = '0'
  document.body.appendChild(ghost)
  event.dataTransfer?.setDragImage(ghost, 0, 0)
  setTimeout(() => ghost.remove(), 0)

  cell.style.opacity = '0.5'
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function onDrop(event: DragEvent, targetCellId: number) {
  event.preventDefault()
  const data = event.dataTransfer?.getData('text/plain')
  if (data == null) return

  const sourceCellId = Number(data)
  if (Number.isNaN(sourceCellId) || sourceCellId === targetCellId) return

  emit('moveWidget', { sourceCellId, targetCellId })
}

function onDragEnd(event: DragEvent) {
  const cell = event.currentTarget as HTMLElement | null
  if (cell) {
    cell.style.opacity = '1'
  }
}
</script>

<template>
  <div
      class="grid h-screen w-screen grid-cols-4 grid-rows-4 gap-4 bg-neutral-900 text-white p-4"
      :style="{'--cols': 4, '--rows': 4}"
  >
    <!-- generiert leere Zellen mit Platzhaltern -->
    <div
        v-for="cellId in 16"
        :key="cellId"
        :id="cellId.toString()"
        class="rounded-xl bg-neutral-800 shadow-inner overflow-hidden"
        draggable="true"
        @dragstart="onDragStart($event, cellId, Boolean(widgets[cellId]))"
        @dragover="onDragOver"
        @drop="onDrop($event, cellId)"
        @dragend="onDragEnd($event)"
    >
      <component
        v-if="widgets[cellId]?.component"
        :is="widgets[cellId]?.component"
        v-bind="widgets[cellId]?.widgetProps ?? {}"
        class="h-full w-full"
      />
      <div v-else class="w-full h-full grid place-items-center text-2xl font-semibold opacity-70">
        {{ String(cellId).padStart(2, '0') }}
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
