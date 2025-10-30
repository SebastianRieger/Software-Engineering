<template>
  <div class="widget-container" :style="containerStyle">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Position, Size } from '../../types'

const props = defineProps<{ position?: Position; size?: Size }>()

const size = computed<Size>(() => props.size ?? { width: 300, height: 200 })

const containerStyle = computed(() => ({
  width: typeof size.value.width === 'number' ? `${size.value.width}px` : (size.value.width as unknown as string),
  height: typeof size.value.height === 'number' ? `${size.value.height}px` : (size.value.height as unknown as string)
}))
</script>

<style scoped>
.widget-container {
  background: var(--color-surface);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
