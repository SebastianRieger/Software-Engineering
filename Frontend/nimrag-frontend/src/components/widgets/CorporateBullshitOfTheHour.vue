<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import type { Ref } from 'vue'
import type { CellSize } from '../../composables/useWidgetResize.ts'
import { useBullshitDerStunde } from '../../composables/useBullshitDerStunde.ts'

const cellId    = inject<number>('cellId', 0)
const cellSizes = inject<Ref<Record<number, CellSize>>>('cellSizes', ref({}))

const size = computed(() => {
  switch (cellSizes.value[cellId]) {
    case 4:  return 'large'
    case 2:  return 'medium'
    default: return 'small'
  }
})

const visibleCount = computed(() => {
  switch (size.value) {
    case 'large':  return 5
    case 'medium': return 3
    default:       return 1
  }
})

const { data, isLoading, error } = useBullshitDerStunde()

const visiblePhrases = computed(() =>
  data.value?.phrases.slice(0, visibleCount.value) ?? []
)

function splitPhrase(phrase: string): { keyword: string; rest: string } {
  const spaceIndex = phrase.indexOf(' ')
  if (spaceIndex === -1) return { keyword: phrase, rest: '' }
  return {
    keyword: phrase.slice(0, spaceIndex),
    rest: phrase.slice(spaceIndex + 1),
  }
}
</script>

<template>
  <div class="bs-widget" :class="`bs-widget--${size}`">

    <!-- Header -->
    <header class="bs-header">
      <span class="bs-logo">Corporate Bullshit of the Hour</span>
      <span v-if="isLoading" class="bs-status bs-status--loading"><span class="bs-dot" /></span>
      <span v-else-if="error" class="bs-status bs-status--error" :title="error">!</span>
      <span v-else class="bs-badge">BS</span>
    </header>

    <!-- Systemzustände -->
    <div v-if="error"          class="bs-empty">Phrases not available</div>
    <div v-else-if="isLoading" class="bs-empty">Loading…</div>
    <div v-else-if="!visiblePhrases.length" class="bs-empty">No phrases</div>

    <!-- Phrasen-Liste -->
    <ul v-else class="bs-list" :key="visiblePhrases.join()">
      <li
        v-for="(phrase, index) in visiblePhrases"
        :key="index"
        class="bs-item"
        :style="{ animationDelay: `${index * 80}ms` }"
      >
        <span class="bs-keyword">{{ splitPhrase(phrase).keyword }}</span>
        <span class="bs-phrase">{{ splitPhrase(phrase).rest }}</span>
      </li>
    </ul>

  </div>
</template>

<style scoped>
/* ── Variablen & Container ─────────────────────────── */
.bs-widget {
  --c-bg:      #111;
  --c-surface: #1a1a1a;
  --c-border:  rgba(255, 255, 255, 0.07);
  --c-text:    #e8e8e8;
  --c-muted:   #666;
  --c-accent:  #8b5cf6;
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
.bs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.bs-logo {
  font-family: var(--font-ui);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #fff;
  opacity: 0.9;
}

.bs-badge {
  font-family: var(--font-ui);
  font-size: 8px;
  letter-spacing: 0.14em;
  color: var(--c-accent);
  border: 1px solid rgba(139, 92, 246, 0.4);
  padding: 1px 5px;
  border-radius: 3px;
  opacity: 0.85;
}

.bs-status {
  font-family: var(--font-ui);
  font-size: 10px;
  color: var(--c-muted);
}

.bs-status--error { color: #c0392b; font-weight: 700; }

.bs-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  background: var(--c-muted);
  border-radius: 50%;
  animation: bs-pulse 1.4s ease-in-out infinite;
}

@keyframes bs-pulse {
  0%, 100% { opacity: 0.3; }
  50%       { opacity: 1;   }
}

/* ── Leer / Fehler ─────────────────────────────────── */
.bs-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-ui);
  font-size: 11px;
  color: var(--c-muted);
  letter-spacing: 0.08em;
}

/* ── Listen-Container ──────────────────────────────── */
.bs-list {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

/* ── Einzelne Phrase ───────────────────────────────── */
.bs-item {
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 10px;
  border-bottom: 1px solid var(--c-border);
  overflow: hidden;
  min-height: 0;
  animation: bs-fadein 0.35s ease both;
}

.bs-item:last-child { border-bottom: none; }

@keyframes bs-fadein {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0);   }
}

.bs-keyword {
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 700;
  color: var(--c-accent);
  flex-shrink: 0;
  white-space: nowrap;
  padding-top: 1px;
  letter-spacing: 0.04em;
}

.bs-phrase {
  font-size: 11px;
  line-height: 1.45;
  color: var(--c-text);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ── Größenvarianten ───────────────────────────────── */
.bs-widget--small .bs-phrase {
  font-size: 13px;
  -webkit-line-clamp: 4;
  line-height: 1.55;
}

.bs-widget--small .bs-keyword {
  font-size: 12px;
}

.bs-widget--medium .bs-phrase {
  font-size: 12px;
}

.bs-widget--large .bs-item {
  padding: 8px 12px;
}

.bs-widget--large .bs-phrase {
  font-size: 13px;
  line-height: 1.5;
}

.bs-widget--large .bs-index {
  font-size: 9px;
  padding-top: 3px;
}
</style>
