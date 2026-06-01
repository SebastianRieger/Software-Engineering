<script setup lang="ts">
import { toRefs, ref, watch, onMounted } from 'vue';
import { useWidgetResize } from '../../composables/useWidgetResize';
import { useWidgetManager } from '../../composables/useWidgetManager';
import { useHoverTrigger } from '../../composables/useHoverTrigger';
import type { CursorPosition } from '../../composables/useHandTracking';
import CellSlot from './CellSlot.vue';

const emit = defineEmits(['widgetsMoved', 'deleteWidget', 'confirmDelete', 'cancelDelete']);

const props = defineProps<{
  isEditMode: boolean
  focusedCellId?: number | null
  isDragging?: boolean
  dragSourceCell?: number | null
  deleteConfirmCell?: number | null
  gestureCursor?: CursorPosition | null
}>();

const { isEditMode, focusedCellId } = toRefs(props);
const { getGridClass, cycleCellSize, getSizeLabel, initializeCell, getVisibleCells } = useWidgetResize();
const { widgetMap } = useWidgetManager();

const draggingCell = ref<number | null>(null);
const resizingCell = ref<number | null>(null);

const { active: ringActive, x: ringX, y: ringY, start: hoverStart, cancel: hoverCancel, move: hoverMove } = useHoverTrigger();

// Gesture-cursor dwell: same trigger logic, driven by hand-tracking position
const gestureOverBtn = ref<string | null>(null)

watch(() => props.gestureCursor, (pos) => {
  if (!isEditMode.value || !pos) {
    if (gestureOverBtn.value !== null) {
      gestureOverBtn.value = null
      hoverCancel()
    }
    return
  }

  const px = (pos.x / 100) * window.innerWidth
  const py = (pos.y / 100) * window.innerHeight
  const fakeEvent = { clientX: px, clientY: py } as MouseEvent

  const el = document.elementFromPoint(px, py)
  const btn = el?.closest('.delete-widget-btn, .resize-widget-btn') as HTMLElement | null

  if (!btn) {
    if (gestureOverBtn.value !== null) {
      gestureOverBtn.value = null
      hoverCancel()
    }
    return
  }

  const cellEl = btn.closest('[data-cell-id]') as HTMLElement | null
  const cellId = cellEl ? Number(cellEl.dataset['cellId']) : NaN
  if (isNaN(cellId)) return

  const type = btn.classList.contains('delete-widget-btn') ? 'delete' : 'resize'
  const key = `${type}-${cellId}`

  if (gestureOverBtn.value === key) {
    hoverMove(fakeEvent)
  } else {
    gestureOverBtn.value = key
    const callback = type === 'delete'
      ? () => onDeleteClick(cellId)
      : () => onResizeClick(cellId)
    hoverStart(fakeEvent, callback)
  }
})

onMounted(() => {
  for (let i = 1; i <= 16; i++) {
    initializeCell(i);
  }
});

function onDragStart(e: DragEvent, index: number) {
  if (!widgetMap.value[index]) return;

  e.dataTransfer?.setData('text/plain', String(index));
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move';
  }

  const ghost = document.createElement('div');
  ghost.style.width = '1px';
  ghost.style.height = '1px';
  ghost.style.opacity = '0';
  document.body.appendChild(ghost);
  e.dataTransfer?.setDragImage(ghost, 0, 0);
  setTimeout(() => ghost.remove(), 0);

  draggingCell.value = index;
}

function onDragOver(e: DragEvent) {
  e.preventDefault();
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move';
  }
}

function onDrop(e: DragEvent, targetIndex: number) {
  e.preventDefault();
  const data = e.dataTransfer?.getData('text/plain');
  if (data == null) return;

  const sourceCellId = Number(data);
  const targetCellId = targetIndex;

  if (Number.isNaN(sourceCellId) || sourceCellId === targetCellId) return;

  draggingCell.value = null;
  emit('widgetsMoved', { sourceCellId, targetCellId });
}

function onDragEnd(_e: DragEvent, index: number) {
  if (draggingCell.value === index) {
    draggingCell.value = null;
  }
}

function onDeleteClick(cellId: number) {
  emit('deleteWidget', cellId);
}

function onResizeClick(cellId: number) {
  cycleCellSize(cellId);
  resizingCell.value = cellId;
  setTimeout(() => { resizingCell.value = null; }, 450);
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
    <div
        v-for="i in getVisibleCells()"
        :key="i"
        :id="String(i)"
        :data-cell-id="i"
      :class="['grid-cell', getGridClass(i), {
        'cell-dragging': draggingCell === i,
        'cell-drag-source': props.isDragging && props.dragSourceCell === i,
        'cell-drag-target': props.isDragging && focusedCellId === i && props.dragSourceCell !== i,
        'cell-delete-confirm': props.deleteConfirmCell === i,
        'grid-cell-focused': isEditMode && focusedCellId === i && !props.isDragging,
      }]"
        :aria-selected="focusedCellId === i"
        draggable="true"
        @dragstart="onDragStart($event, i)"
        @dragover="onDragOver"
        @drop="onDrop($event, i)"
        @dragend="onDragEnd($event, i)"
    >
      <!-- Widget oder Platzhalter -->
      <CellSlot
          v-if="widgetMap[i]"
          :cell-id="i"
          :component="widgetMap[i]"
          :is-edit-mode="isEditMode"
          class="w-full h-full"
      />
      <div v-else class="w-full h-full grid place-items-center text-2xl font-semibold opacity-70">
        {{ String(i).padStart(2, '0') }}
      </div>

      <!-- Delete-Button: Obere rechte Ecke (Maus-Fallback) -->
      <button
          v-if="isEditMode && widgetMap[i] && !props.isDragging && props.deleteConfirmCell !== i"
          class="delete-widget-btn"
          @click.stop
          @mouseenter="(e) => hoverStart(e, () => onDeleteClick(i))"
          @mouseleave="hoverCancel"
          @mousemove="hoverMove"
          title="Widget löschen"
      >
        ×
      </button>

      <!-- Delete-Confirm Overlay -->
      <div v-if="props.deleteConfirmCell === i" class="delete-confirm-overlay">
        <span class="delete-confirm-label">Löschen?</span>
        <div class="delete-confirm-actions">
          <button class="confirm-btn confirm-btn--yes" @click.stop="emit('confirmDelete', i)">✓</button>
          <button class="confirm-btn confirm-btn--no" @click.stop="emit('cancelDelete')">×</button>
        </div>
      </div>

      <!-- Resize-Button: Untere rechte Ecke -->
      <button
          v-if="isEditMode && widgetMap[i] && !props.isDragging"
          :class="['resize-widget-btn', { 'resize-active': resizingCell === i }]"
          @click.stop
          @mouseenter="(e) => hoverStart(e, () => onResizeClick(i))"
          @mouseleave="hoverCancel"
          @mousemove="hoverMove"
          :title="`Größe: ${getSizeLabel(i)}`"
      >
        ⤡
      </button>

    </div>
  </div>

  <!-- Hover ring: follows cursor while dwell timer runs -->
  <Teleport to="body">
    <div
      v-if="ringActive"
      class="hover-ring"
      :style="{ left: ringX + 'px', top: ringY + 'px' }"
    >
      <svg width="40" height="40" viewBox="0 0 40 40">
        <circle cx="20" cy="20" r="16" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="1.5" />
        <circle cx="20" cy="20" r="16" fill="none" stroke="rgba(255,255,255,0.9)" stroke-width="2"
          stroke-linecap="round" stroke-dasharray="100.53" class="ring-arc" />
      </svg>
    </div>
  </Teleport>
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

.grid-cell-focused {
  box-shadow:
    inset 0 0 0 2px rgba(255, 255, 255, 0.95),
    0 0 0 4px rgba(255, 255, 255, 0.2);
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

/* Resize-Button Styling */
.resize-widget-btn {
  position: absolute;
  visibility: visible;
  bottom: 8px;
  right: 8px;
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #3a3a3a 0%, #2a2a2a 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 99;
  transition: transform 200ms ease, box-shadow 200ms ease;
  padding: 0;
  font-weight: 600;
  overflow: hidden;
}

/* Confirm overlay — only opacity animates, no paint cost */
.resize-widget-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  opacity: 0;
  pointer-events: none;
}

.resize-widget-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
}

/* Post-hold confirmation: calm arrival, then fade back to idle */
.resize-widget-btn.resize-active {
  animation: resize-confirm-scale 450ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.resize-widget-btn.resize-active::after {
  animation: resize-confirm-fill 450ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

@keyframes resize-confirm-scale {
  0%   { transform: scale(1.05); }
  30%  { transform: scale(1); }
  100% { transform: scale(1); }
}

@keyframes resize-confirm-fill {
  0%   { opacity: 1; }
  35%  { opacity: 1; }
  100% { opacity: 0; }
}

.cell-dragging {
  opacity: 0.5;
  transition: opacity 0.2s ease;
}

.cell-drop-target {
  box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.6);
  transition: box-shadow 0.2s ease;
}

/* Gesture drag states */
.cell-drag-source {
  opacity: 0.28;
  border: 2px dashed rgba(255, 255, 255, 0.35);
  transition: opacity 180ms ease, border 180ms ease;
}

.cell-drag-target {
  box-shadow:
    inset 0 0 0 2px rgba(255, 255, 255, 0.9),
    0 0 0 4px rgba(255, 255, 255, 0.18);
  background: #333333;
  transition: box-shadow 120ms ease, background 120ms ease;
}

/* Delete confirm state */
.cell-delete-confirm {
  box-shadow: inset 0 0 0 2px rgba(239, 68, 68, 0.9);
  animation: delete-pulse 0.8s ease-in-out infinite alternate;
}

@keyframes delete-pulse {
  from { box-shadow: inset 0 0 0 2px rgba(239, 68, 68, 0.7); }
  to   { box-shadow: inset 0 0 0 2px rgba(239, 68, 68, 1), 0 0 0 4px rgba(239, 68, 68, 0.18); }
}

/* Delete confirm overlay */
.delete-confirm-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.72);
  border-radius: inherit;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  z-index: 110;
}

.delete-confirm-label {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(239, 68, 68, 0.9);
}

.delete-confirm-actions {
  display: flex;
  gap: 8px;
}

.confirm-btn {
  width: 34px;
  height: 34px;
  border-radius: 6px;
  border: none;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 150ms ease, background 150ms ease;
}

.confirm-btn:active { transform: scale(0.92); }

.confirm-btn--yes {
  background: rgba(239, 68, 68, 0.9);
  color: #ffffff;
}

.confirm-btn--yes:hover { background: rgb(239, 68, 68); }

.confirm-btn--no {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.confirm-btn--no:hover { background: rgba(255, 255, 255, 0.18); }

@media (prefers-reduced-motion: reduce) {
  .cell-delete-confirm { animation: none; }
  .confirm-btn { transition: none; }
  .resize-widget-btn.resize-active,
  .resize-widget-btn.resize-active::after { animation: none; }
  .resize-widget-btn.resize-active::after { opacity: 1; }
}

/* Hover-dwell ring — teleported to body, not scoped */
</style>

<style>
.hover-ring {
  position: fixed;
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 99999;
}

.hover-ring svg {
  display: block;
  transform: rotate(-90deg);
}

@keyframes ring-fill {
  from { stroke-dashoffset: 100.53; }
  to   { stroke-dashoffset: 0; }
}

.ring-arc {
  stroke-dashoffset: 100.53;
  animation: ring-fill 1s linear forwards;
}
</style>
