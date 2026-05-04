<script setup lang="ts">
import { defineEmits, defineProps, toRefs, ref, onMounted } from 'vue';
import { useWidgetResize } from '../../composables/useWidgetResize';

const emit = defineEmits(['widgetsMoved', 'deleteWidget']);

const props = defineProps<{
  isEditMode: boolean
}>();

const { isEditMode } = toRefs(props);
const { getGridClass, cycleCellSize, getSizeLabel, initializeCell, getVisibleCells } = useWidgetResize();

// Reaktiver "Refresh-Trigger" für die Delete-Buttons
const widgetVersion = ref(0);
const resizingCell = ref<number | null>(null);

// Grid-Zellen initialisieren
onMounted(() => {
  for (let i = 1; i <= 16; i++) {
    initializeCell(i);
  }
});

// Hilfsfunktion um zu prüfen ob eine Zelle ein Widget hat
function hasWidget(cellId: number): boolean {
  const mount = document.getElementById(`cell-content-${cellId}`)
  if (!mount) return false

  const hasPlaceholder = mount.querySelector('.opacity-70')
  return !hasPlaceholder
}

// 4x4 Grid -> 16 Zellen
function onDragStart(e: DragEvent, index: number) {
  const cellId = index
  const cell = document.getElementById(cellId.toString())
  if (!cell) return

  const hasPlaceholder = cell.querySelector('.opacity-70')
  if (hasPlaceholder) return

  e.dataTransfer?.setData('text/plain', String(cellId))
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
  }

  const ghost = document.createElement('div')
  ghost.style.width = '1px'
  ghost.style.height = '1px'
  ghost.style.opacity = '0'
  document.body.appendChild(ghost)
  e.dataTransfer?.setDragImage(ghost, 0, 0)
  setTimeout(() => ghost.remove(), 0)

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

  // DOM-Nodes wirklich verschieben (nicht innerHTML kopieren!)
  // → Vue-App-Instanzen bleiben an ihrem Container-Div hängen
  const sourceChild = sourceMount.firstElementChild
  const targetChild = targetMount.firstElementChild

  if (sourceChild && targetChild) {
    const anchor = document.createComment('swap')
    targetMount.replaceChild(anchor, targetChild)   // targetChild kurz rausnehmen
    sourceMount.replaceChild(targetChild, sourceChild)  // sourceChild → targetChild
    targetMount.replaceChild(sourceChild, anchor)   // anchor → sourceChild
  } else if (sourceChild) {
    targetMount.appendChild(sourceChild)  // leere Zelle: einfach rüberbewegen
  } else if (targetChild) {
    sourceMount.appendChild(targetChild)
  }

  const sourceCell = sourceMount.parentElement as HTMLElement | null
  if (sourceCell) sourceCell.style.opacity = '1'

  widgetVersion.value++

  emit('widgetsMoved', { sourceCellId, targetCellId })
}

function onDragEnd(e: DragEvent, index: number) {
  e; //damit kein Fehler in IDE angezeigt wird
  const cellId = index
  const cell = document.getElementById(cellId.toString())
  if (cell) cell.style.opacity = '1'
}

// Delete-Button-Click kapseln, damit wir refreshen können
function onDeleteClick(cellId: number) {
  emit('deleteWidget', cellId)

  // Parent räumt DOM auf (Platzhalter rein) → danach neu prüfen
  setTimeout(() => {
    widgetVersion.value++
  }, 0)
}

// Resize-Button-Click Handler
function onResizeClick(cellId: number) {
  cycleCellSize(cellId);

  // Visuelles Feedback
  resizingCell.value = cellId;
  setTimeout(() => {
    resizingCell.value = null;
  }, 200);

  // Force UI-Update für getVisibleCells()
  widgetVersion.value++;
}
</script>


<template>
  <div
      class="grid bg-neutral-900 text-white p-4"
      style="
        width: 100vw;
        height: 100vh;
        grid-template-columns: repeat(4, 1fr);
        grid-template-rows: repeat(4, 1fr);
        gap: 1rem;
        overflow: hidden;
      "
  >
    <!-- generiert Zellen basierend auf verfügbarem Platz -->
    <div
        v-for="i in getVisibleCells()"
        :key="i"
        :id="String(i)"
        :class="['grid-cell', getGridClass(i)]"
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

      <!-- Delete-Button: Obere rechte Ecke -->
      <button
          v-if="isEditMode && widgetVersion >= 0 && hasWidget(i)"
          class="delete-widget-btn"
          @click.stop="onDeleteClick(i)"
          title="Widget löschen"
      >
        ×
      </button>

      <!-- Resize-Button: Untere rechte Ecke -->
      <button
          v-if="isEditMode && hasWidget(i)"
          :class="['resize-widget-btn', { 'resize-active': resizingCell === i }]"
          @click.stop="onResizeClick(i)"
          :title="`Größe: ${getSizeLabel(i)}`"
      >
        ⤡
      </button>
    </div>
  </div>
</template>

<style scoped>
.grid-cell {
  position: relative;
  transition: all 0.3s ease;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  background: #262626;
  border-radius: 0.75rem;
  box-shadow: inset 0 1px 2px 0 rgba(0, 0, 0, 0.5);
}

/* Grid-Spanning für verschiedene Größen */
.col-span-2 {
  grid-column: span 2;
}

.row-span-2 {
  grid-row: span 2;
}

.col-span-2.row-span-2 {
  grid-column: span 2;
  grid-row: span 2;
}

/* Delete-Button Styling */
.delete-widget-btn {
  position: absolute;
  visibility: visible;
  top: 8px;
  right: 8px;
  width: 32px;
  height: 32px;
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
  padding: 0;
}

.delete-widget-btn:hover {
  background: rgb(239, 68, 68);
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.5);
}

/* Resize-Button Styling mit Tailwind */
.resize-widget-btn {
  position: absolute;
  visibility: visible;
  bottom: 8px;
  right: 8px;
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 99;
  transition: all 0.2s ease;
  padding: 0;
  font-weight: 600;
}

.resize-widget-btn:hover {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.5);
}

.resize-widget-btn:active {
  transform: scale(0.95);
}

.resize-widget-btn.resize-active {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  animation: resize-pulse 0.3s ease-out;
}

@keyframes resize-pulse {
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  }
  50% {
    transform: scale(1.15);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 8px rgba(16, 185, 129, 0);
  }
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