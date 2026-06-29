<script setup lang="ts">
import { computed } from 'vue'
import type { CursorPosition } from '../../composables/useHandTracking'

const props = defineProps<{
  cursor: CursorPosition | null
  isDragging: boolean
  dragWidgetName?: string | null
}>()

const style = computed(() => {
  if (!props.cursor) return {}
  return {
    left: `${props.cursor.x}%`,
    top: `${props.cursor.y}%`,
  }
})
</script>

<template>
  <Transition name="cursor-fade">
    <div v-if="cursor" class="cursor-layer" aria-hidden="true">
      <div class="cursor-dot" :class="{ 'cursor-dot--grabbing': isDragging }" :style="style">
        <div v-if="isDragging && dragWidgetName" class="drag-chip">
          {{ dragWidgetName }}
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.cursor-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 2000;
}

.cursor-dot {
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #ffffff;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.18);
  transition: width 120ms ease, height 120ms ease, background 120ms ease;
}

.cursor-dot--grabbing {
  width: 20px;
  height: 20px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow:
    0 0 0 4px rgba(255, 255, 255, 0.22),
    0 0 20px rgba(255, 255, 255, 0.12);
}

.drag-chip {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 9999px;
  padding: 4px 10px;
  white-space: nowrap;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.9);
  text-transform: uppercase;
}

.cursor-fade-enter-active,
.cursor-fade-leave-active {
  transition: opacity 150ms ease;
}

.cursor-fade-enter-from,
.cursor-fade-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .cursor-dot,
  .cursor-fade-enter-active,
  .cursor-fade-leave-active {
    transition: none;
  }
}
</style>
