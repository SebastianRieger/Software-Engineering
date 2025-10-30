<template>
  <button
    :class="[
      'smart-button',
      `smart-button--${variant}`,
      `smart-button--${size}`,
      { 'smart-button--disabled': disabled }
    ]"
    :disabled="disabled"
    @click="handleClick"
  >
    <span v-if="loading" class="smart-button__loader">
      <slot name="loader">
        <span class="loader-dots"></span>
      </slot>
    </span>
    <slot v-else></slot>
  </button>
</template>

<script setup lang="ts">
import { } from 'vue'

interface Props {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  disabled: false,
  loading: false
})

const emit = defineEmits<{ (e: 'click', event: MouseEvent): void }>()

const handleClick = (event: MouseEvent) => {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}
</script>

<style scoped>
.smart-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  font-weight: 500;
  transition: all 0.2s;
  cursor: pointer;
  outline: none;
  border: none;
}

.smart-button--primary {
  background-color: var(--color-primary);
  color: white;
}

.smart-button--primary:hover {
  opacity: 0.9;
}

.smart-button--secondary {
  background-color: var(--color-secondary);
  color: white;
}

.smart-button--ghost {
  background-color: transparent;
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
}

.smart-button--danger {
  background-color: var(--color-error);
  color: white;
}

.smart-button--sm {
  padding: 0.5rem 1rem;
  font-size: var(--font-size-sm);
}

.smart-button--md {
  padding: 0.75rem 1.5rem;
  font-size: var(--font-size-base);
}

.smart-button--lg {
  padding: 1rem 2rem;
  font-size: var(--font-size-lg);
}

.smart-button--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.smart-button__loader {
  display: inline-block;
  position: relative;
  width: 1em;
  height: 1em;
}

.loader-dots {
  position: relative;
  width: 1em;
  height: 1em;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-color: currentColor transparent currentColor transparent;
  animation: loader-spin 1s linear infinite;
}

@keyframes loader-spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>