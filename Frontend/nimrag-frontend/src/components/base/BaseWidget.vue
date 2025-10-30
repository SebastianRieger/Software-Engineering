<template>
  <div
    class="base-widget"
    :class="[ `base-widget--${type}`, { 'is-loading': isLoading } ]"
    :style="widgetStyle"
  >
    <div class="base-widget__header">
      <h3 class="base-widget__title">{{ title }}</h3>
      <div class="base-widget__actions">
        <smart-button
          v-if="isRefreshable"
          variant="ghost"
          size="sm"
          :loading="isLoading"
          @click="refresh"
        >
          <i class="fas fa-sync"></i>
        </smart-button>
        <smart-button variant="ghost" size="sm" @click="toggleSettings">
          <i class="fas fa-cog"></i>
        </smart-button>
      </div>
    </div>

    <div v-if="isLoading" class="base-widget__loader">
      <slot name="loader">
        <div class="loader">Loading...</div>
      </slot>
    </div>

    <div v-else-if="error" class="base-widget__error">
      <slot name="error" :error="error">
        <p>{{ error.message }}</p>
      </slot>
    </div>

    <div v-else class="base-widget__content">
      <slot></slot>
    </div>

    <teleport to="body">
      <modal v-if="showSettings" @close="toggleSettings" :isOpen="showSettings" />
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { WidgetType } from '../../types'
import SmartButton from '../ui/SmartButton.vue'
import Modal from '../ui/Modal.vue'

interface Props {
  type: WidgetType
  title: string
  isLoading?: boolean
  error?: Error | null
  isRefreshable?: boolean
  width?: number | string
  height?: number | string
}

const props = withDefaults(defineProps<Props>(), {
  isLoading: false,
  error: null,
  isRefreshable: true,
  width: '100%',
  height: 'auto'
})

const emit = defineEmits<{ (e: 'refresh'): void; (e: 'settings-updated', settings: any): void }>()

const showSettings = ref(false)

const widgetStyle = computed(() => ({
  width: typeof props.width === 'number' ? `${props.width}px` : props.width,
  height: typeof props.height === 'number' ? `${props.height}px` : props.height
}))

const refresh = () => {
  emit('refresh')
}

const toggleSettings = () => {
  showSettings.value = !showSettings.value
}
</script>

<style scoped>
.base-widget {
  background: var(--color-surface);
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s ease;
}

.base-widget__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) var(--spacing-md);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.base-widget__title {
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
}

.base-widget__actions {
  display: flex;
  gap: var(--spacing-xs);
}

.base-widget__content {
  padding: var(--spacing-md);
}

.base-widget__loader,
.base-widget__error {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-md);
  min-height: 100px;
}

.base-widget__error {
  color: var(--color-error);
}

.loader {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-primary);
  border-radius: 50%;
  border-top-color: transparent;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.dark .base-widget {
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}
</style>