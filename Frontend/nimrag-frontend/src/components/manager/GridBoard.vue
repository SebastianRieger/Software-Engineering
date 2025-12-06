<script setup lang="ts">
import { defineEmits, defineProps, toRefs } from 'vue';

const emit = defineEmits(['widgetsMoved', 'deleteWidget']);

const props = defineProps<{
  isEditMode: boolean
}>();

const { isEditMode } = toRefs(props);

// Hilfsfunktion um zu prüfen ob eine Zelle ein Widget hat
function hasWidget(cellId: number): boolean {
  const mount = document.getElementById(`cell-content-${cellId}`)
  if (!mount) return false

  // Prüfe ob die Zelle einen Platzhalter hat (keine Widget)
  const hasPlaceholder = mount.querySelector('.opacity-70')
  return !hasPlaceholder
}

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

  const sourceMount = document.getElementById(`cell-content-${sourceCellId}`)
  const targetMount = document.getElementById(`cell-content-${targetCellId}`)

  if (!sourceMount || !targetMount) return

  // Inhalte tauschen innerhalb der Mount-Container
  const sourceContent = sourceMount.innerHTML
  const targetContent = targetMount.innerHTML

  sourceMount.innerHTML = targetContent
  targetMount.innerHTML = sourceContent

  //visuelles Feedback wiederherstellen
  const sourceCell = sourceMount.parentElement as HTMLElement | null
  if (sourceCell) sourceCell.style.opacity = '1'

  // Vue-Event damit ModuleManager die Widget-Map updaten kann
  emit('widgetsMoved', {
    sourceCellId,
    targetCellId
  })
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
        v-for="i in 16"
        :key="i"
        class="grid-cell rounded-xl bg-neutral-800 shadow-inner overflow-hidden"
        draggable="true"
        @dragstart="onDragStart($event, i)"
        @dragover="onDragOver"
        @drop="onDrop($event, i)"
        @dragend="onDragEnd($event, i)"
    >
      <!-- Mount-Container für Widget-Inhalt -->
      <div
          class="w-full h-full"
          :id="`cell-content-${i}`"
      >
        <!--Platzhalter, bis ein Widget gemountet wird -->
        <div class="w-full h-full grid place-items-center text-2xl font-semibold opacity-70">
          {{ String(i).padStart(2, '0') }}
        </div>
      </div>

      <!-- Delete-Button von Vue kontrolliert -->
      <button
          v-if="isEditMode  && hasWidget(i)"
          class="delete-widget-btn"
          @click.stop="emit('deleteWidget', i)"
      >
        x
      </button>
    </div>
  </div>
</template>

<style scoped>
.grid-cell {
  position: relative;
}

.delete-widget-btn {
  position: absolute;
  visibility: visible;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  background: rgba(239, 68, 68, 0.9);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 20px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  transition: all 0.2s;
  line-height: 1;
  padding: 0;
}

.delete-widget-btn:hover {
  background: rgb(239, 68, 68);
  transform: scale(1.1);
}
.cell-dragging {
  opacity: 0.5;
  transition: opacity 0.2s ease;
}

.cell-drop-target {
  box-shadow: inset 0 0 0 2px rgba(80, 160, 255, 0.6);
  transition: box-shadow 0.2s ease;
}
</style>