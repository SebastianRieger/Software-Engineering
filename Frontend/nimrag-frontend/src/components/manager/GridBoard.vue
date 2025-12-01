<script setup lang="ts">
import { defineEmits } from 'vue';

// Event-Emitter definieren
const emit = defineEmits(['widgetsMoved']);

// 4x4 Grid -> 16 Zellen
function onDragStart(e: DragEvent, index: number) {
  const cellId = index // Cell IDs sind 1-basiert
  const cell = document.getElementById(cellId.toString())
  if (!cell) return

  // Prüfe ob die Zelle ein Widget enthält (kein Platzhalter)
  const hasPlaceholder = cell.querySelector('.opacity-70')
  if (hasPlaceholder) return // Leere Zellen können nicht gezogen werden

  e.dataTransfer?.setData('text/plain', String(cellId))
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
  }

  // Ghost Image
  const ghost = document.createElement('div')
  ghost.style.width = '1px'
  ghost.style.height = '1px'
  ghost.style.opacity = '0'
  document.body.appendChild(ghost)
  e.dataTransfer?.setDragImage(ghost, 0, 0)
  setTimeout(() => ghost.remove(), 0)

  // Visuelles Feedback
  cell.style.opacity = '0.5'
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
}

function onDrop(e: DragEvent, targetIndex: number) {
  e.preventDefault()
  const data = e.dataTransfer?.getData('text/plain')
  if (data == null) return

  const sourceCellId = Number(data)
  const targetCellId = targetIndex

  if (Number.isNaN(sourceCellId) || sourceCellId === targetCellId) return

  const sourceCell = document.getElementById(sourceCellId.toString())
  const targetCell = document.getElementById(targetCellId.toString())

  if (!sourceCell || !targetCell) return

  // Inhalte tauschen (HTML swap)
  const sourceContent = sourceCell.innerHTML
  const targetContent = targetCell.innerHTML

  sourceCell.innerHTML = targetContent
  targetCell.innerHTML = sourceContent

  // Styling zurücksetzen
  sourceCell.style.opacity = '1'

  // Classes auch tauschen
  const sourceClasses = sourceCell.className
  const targetClasses = targetCell.className
  sourceCell.className = targetClasses
  targetCell.className = sourceClasses

  // Event emittieren, um ModuleManager zu informieren
  emit('widgetsMoved', {
    sourceCellId: sourceCellId,
    targetCellId: targetCellId
  });
}

function onDragEnd(e: DragEvent, index: number) {
  e; //damit kein Fehler in IDE angezeigt wird
  const cellId = index
  const cell = document.getElementById(cellId.toString())
  if (cell) cell.style.opacity = '1'
}
</script>

<template>
  <div
      class="grid h-screen w-screen grid-cols-4 grid-rows-4 gap-4 bg-neutral-900 text-white p-4"
      :style="{'--cols': 4, '--rows': 4}"
  >
    <!-- generiert leere Zellen mit Platzhaltern -->
    <div
        v-for="(i) in 16"
        :key="i"
        :id="(i).toString()"
        class="rounded-xl bg-neutral-800 shadow-inner overflow-hidden"
        draggable="true"
        @dragstart="onDragStart($event, i)"
        @dragover="onDragOver"
        @drop="onDrop($event, i)"
        @dragend="onDragEnd($event, i)"
    >
      <div class="w-full h-full grid place-items-center text-2xl font-semibold opacity-70">
        {{ String(i).padStart(2, '0') }}
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Optional: Zusätzliche Styles für Drag-and-Drop Effekte */
.cell-dragging {
  opacity: 0.5;
  transition: opacity 0.2s ease;
}

.cell-drop-target {
  box-shadow: inset 0 0 0 2px rgba(80, 160, 255, 0.6);
  transition: box-shadow 0.2s ease;
}
</style>