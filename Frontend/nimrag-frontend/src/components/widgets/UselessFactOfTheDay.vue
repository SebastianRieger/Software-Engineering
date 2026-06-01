<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import type { Ref } from 'vue'
import type { CellSize } from '../../composables/useWidgetResize.ts'
import { useFaktDesTages } from '../../composables/useFaktDesTages.ts'

const cellId    = inject<number>('cellId', 0)
const cellSizes = inject<Ref<Record<number, CellSize>>>('cellSizes', ref({}))

const size = computed(() => {
  switch (cellSizes.value[cellId]) {
    case 4:  return 'large'
    case 2:  return 'medium'
    default: return 'small'
  }
})

const { fact, isLoading, error } = useFaktDesTages()
</script>

<template>
  <div class="fdt-widget" :class="`fdt-widget--${size}`">

    <!-- Header -->
    <header class="fdt-header">
      <span class="fdt-logo">Useless Fact of the Day</span>
      <span v-if="isLoading" class="fdt-status fdt-status--loading"><span class="fdt-dot" /></span>
      <span v-else-if="error" class="fdt-status fdt-status--error" :title="error">!</span>
      <span v-else class="fdt-icon" aria-hidden="true">✦</span>
    </header>

    <!-- Systemzustände -->
    <div v-if="error"          class="fdt-empty">Fakt nicht verfügbar</div>
    <div v-else-if="isLoading" class="fdt-empty">Lädt…</div>
    <div v-else-if="!fact"     class="fdt-empty">Kein Fakt</div>

    <!-- Fakt-Text -->
    <div v-else class="fdt-body">
      <p class="fdt-text">{{ fact.text }}</p>
    </div>

  </div>
</template>

<style scoped>
/* ── Variablen & Container ─────────────────────────── */
.fdt-widget {
  --c-bg:      #111;
  --c-surface: #1a1a1a;
  --c-border:  rgba(255, 255, 255, 0.07);
  --c-text:    #e8e8e8;
  --c-muted:   #666;
  --c-accent:  #c8a96e;
  --font-head: 'Georgia', 'Times New Roman', serif;
  --font-ui:   'DM Mono', 'Courier New', monospace;

  width: 100%;
  height: 100%;
  background: var(--c-bg);
  color: var(--c-text);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
  font-family: var(--font-head);
  user-select: none;
}

/* ── Header ────────────────────────────────────────── */
.fdt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.fdt-logo {
  font-family: var(--font-ui);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #fff;
  opacity: 0.9;
}

.fdt-icon {
  font-size: 10px;
  color: var(--c-accent);
  opacity: 0.75;
}

.fdt-status {
  font-family: var(--font-ui);
  font-size: 10px;
  color: var(--c-muted);
}

.fdt-status--error { color: #c0392b; font-weight: 700; }

.fdt-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  background: var(--c-muted);
  border-radius: 50%;
  animation: fdt-pulse 1.4s ease-in-out infinite;
}

@keyframes fdt-pulse {
  0%, 100% { opacity: 0.3; }
  50%       { opacity: 1;   }
}

/* ── Leer / Fehler ─────────────────────────────────── */
.fdt-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-ui);
  font-size: 11px;
  color: var(--c-muted);
  letter-spacing: 0.08em;
}

/* ── Body ──────────────────────────────────────────── */
.fdt-body {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 10px 12px;
  overflow: hidden;
  min-height: 0;
}

/* ── Fakt-Text ─────────────────────────────────────── */
.fdt-text {
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
  color: var(--c-text);
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Anführungszeichen-Akzent oben links */
.fdt-body::before {
  content: '\201E';
  font-size: 48px;
  line-height: 1;
  color: var(--c-accent);
  opacity: 0.18;
  position: absolute;
  top: 28px;
  left: 8px;
  font-family: var(--font-head);
  pointer-events: none;
}

.fdt-widget {
  position: relative;
}

/* ── Größenvarianten ───────────────────────────────── */
.fdt-widget--small .fdt-text {
  font-size: 13px;
  -webkit-line-clamp: 3;
}

.fdt-widget--medium .fdt-text {
  font-size: 16px;
  -webkit-line-clamp: 4;
}

.fdt-widget--large .fdt-text {
  font-size: 20px;
  line-height: 1.65;
  -webkit-line-clamp: 6;
}

.fdt-widget--large .fdt-body {
  padding: 16px 18px;
  align-items: flex-start;
}

.fdt-widget--large .fdt-body::before {
  font-size: 72px;
  top: 36px;
  left: 12px;
}
</style>
