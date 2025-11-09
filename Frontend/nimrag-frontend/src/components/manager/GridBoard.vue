<!-- src/components/GridBoard.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import ModuleManager from './ModuleManager.vue'

type Cell = string | null

// 4x4 Grid -> 16 Zellen
const COLS = 4
const ROWS = 4
const total = COLS * ROWS

// Initial-Belegung: Uhr in Zelle 0, Wetter in Zelle 1, Rest leer
const grid = ref<Cell[]>(Array.from({ length: total }, (_, i) =>
    i === 0 ? 'ClockWidget' : i === 1 ? 'WeatherWidget' : null
))

function onDragStart(e: DragEvent, index: number) {
  // Nur echte Module dürfen gezogen werden
  if (!grid.value[index]) return
  e.dataTransfer?.setData('text/plain', String(index))
  e.dataTransfer?.setDragImage?.(createGhost(), 0, 0)
}

function onDragOver(e: DragEvent) {
  // Erlaubt Drop (sonst feuert 'drop' nicht)
  e.preventDefault()
}

function onDrop(e: DragEvent, targetIndex: number) {
  e.preventDefault()
  const data = e.dataTransfer?.getData('text/plain')
  if (data == null) return
  const sourceIndex = Number(data)
  if (Number.isNaN(sourceIndex) || sourceIndex === targetIndex) return

  const src = grid.value[sourceIndex]
  const dst = grid.value[targetIndex]

  // Verhalten:
  // - Drop auf leere Zelle: verschieben, Quelle wird null (gewünschtes "leeres div")
  // - Drop auf belegte Zelle: tauschen
  if (src == null) return
  if (dst == null) {
    grid.value[targetIndex] = src
    grid.value[sourceIndex] = null
  } else {
    grid.value[targetIndex] = src
    grid.value[sourceIndex] = dst
  }
}

// Kleiner, unsichtbarer Drag-Ghost, damit das Modul nicht unter dem Cursor „wegzuckt“
function createGhost() {
  const el = document.createElement('div')
  el.style.width = '1px'
  el.style.height = '1px'
  el.style.opacity = '0'
  document.body.appendChild(el)
  return el
}
</script>

<template>
  <div
      class="grid h-screen w-screen grid-cols-4 grid-rows-4 gap-4 bg-neutral-900 text-white p-4"
      :style="{'--cols': 4, '--rows': 4}"
  >
    <div
        v-for="(cell, i) in grid"
        :key="i"
        class="rounded-xl bg-neutral-800 shadow-inner overflow-hidden p-3 relative"
        :class="{
        // Visuelle Hilfe für leere Slots
        'border border-dashed border-neutral-700': cell === null
      }"
        draggable="true"
        @dragstart="onDragStart($event, i)"
        @dragover="onDragOver"
        @drop="onDrop($event, i)"
    >
      <!-- Belegte Zelle: Modul rendern -->
      <ModuleManager
          v-if="cell"
          :module="cell"
          class="w-full h-full"
      />

      <!-- Leere Zelle: Platzhalter-Zahl / Hint -->
      <div
          v-else
          class="w-full h-full grid place-items-center text-2xl font-semibold opacity-60 select-none"
      >
        {{ String(i + 1).padStart(2, '0') }}
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>