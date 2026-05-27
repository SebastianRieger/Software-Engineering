<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, inject, computed } from 'vue'
import type { Ref } from 'vue'
import type { CellSize } from '../../composables/useWidgetResize'
import { useClockWidgetMode } from '../../composables/useClockWidgetMode'
import AnalogClock from '../internal/AnalogClock.vue'

const now = ref(new Date())
let timer: number

const cellId = inject<number>('cellId', 0)
const cellSizes = inject<Ref<Record<number, CellSize>>>('cellSizes', ref({}))
const { clockAnalogMode } = useClockWidgetMode()

const isInGrid = computed(() => cellId !== 0)

const cellSize = computed(() => {
  return cellSizes.value[cellId] ?? 1
})

const clockSize = computed(() => {
  switch (cellSize.value) {
    case 4:  return '8rem'
    case 2:  return '6rem'
    default: return '4rem'
  }
})

onMounted(() => { timer = window.setInterval(() => now.value = new Date(), 1000) })
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="w-full h-full card flex flex-col justify-center items-center p-0">
    <template v-if="isInGrid && clockAnalogMode">
      <AnalogClock :time="now" :size="cellSize" />
    </template>
    <template v-else>
      <p :style="{ fontSize: clockSize, margin: 0 }">{{ now.toLocaleTimeString() }}</p>
    </template>
  </div>
</template>

<style scoped>
.card {
  background: #000000;
  color: #eee;
  padding: 0;
}
</style>