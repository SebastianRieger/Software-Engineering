<template>
  <transition name="modal-fade">
    <div v-if="isOpen" class="modal-backdrop" @click.self="onBackdropClick">
      <div class="modal" role="dialog" aria-modal="true" :aria-label="ariaLabel">
        <header v-if="$slots.header" class="modal__header"><slot name="header" /></header>
        <section class="modal__body"><slot /></section>
        <footer v-if="$slots.footer" class="modal__footer"><slot name="footer" /></footer>
        <button class="modal__close" @click="close" aria-label="Close modal">✕</button>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { defineEmits, defineProps, toRef } from 'vue'

const props = defineProps<{ isOpen: boolean; closeOnBackdrop?: boolean; ariaLabel?: string }>()
const emit = defineEmits<{ (e: 'update:isOpen', value: boolean): void; (e: 'close'): void }>()

const closeOnBackdrop = toRef(props, 'closeOnBackdrop')
const ariaLabel = props.ariaLabel ?? 'Modal dialog'

function close() {
  emit('update:isOpen', false)
  emit('close')
}

function onBackdropClick() {
  if (closeOnBackdrop.value ?? true) close()
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
}
.modal {
  background: var(--color-surface, #fff);
  color: var(--color-text, #000);
  min-width: 320px;
  max-width: 90%;
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  position: relative;
  padding: 1rem;
}
.modal__header {
  font-weight: 600;
  margin-bottom: 0.5rem;
}
.modal__body { padding: 0.5rem 0; }
.modal__footer { margin-top: 0.75rem; display:flex; gap:0.5rem; justify-content:flex-end }
.modal__close {
  position: absolute;
  right: 0.5rem;
  top: 0.5rem;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 1rem;
}
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.15s ease }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0 }
</style>
