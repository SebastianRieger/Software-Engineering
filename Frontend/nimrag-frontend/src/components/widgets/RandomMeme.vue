<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import type { Ref } from 'vue'
import type { CellSize } from '../../composables/useWidgetResize.ts'
import type { MemeItem } from '../../types/meme.ts'
import { useRandomMeme } from '../../composables/useRandomMeme.ts'

const cellId    = inject<number>('cellId', 0)
const cellSizes = inject<Ref<Record<number, CellSize>>>('cellSizes', ref({}))

const size = computed(() => {
  switch (cellSizes.value[cellId]) {
    case 4:  return 'large'
    case 2:  return 'medium'
    default: return 'small'
  }
})

// small=2, medium=4, large=2
const visibleCount = computed(() => size.value === 'medium' ? 4 : 2)

const { memes, isLoading, error, onImageError } = useRandomMeme()

const visibleMemes = computed(() => memes.value.slice(0, visibleCount.value))
const currentSubreddit = computed(() => memes.value[0]?.subreddit ?? null)

// Pick the right preview resolution per size to save bandwidth
function resolveUrl(meme: MemeItem): string {
  const { image_url, previews } = meme
  if (size.value === 'small')  return previews[1] ?? previews[0] ?? image_url
  if (size.value === 'medium') return previews[2] ?? previews[1] ?? image_url
  return previews[3] ?? image_url
}
</script>

<template>
  <div class="rm-widget" :class="`rm-widget--${size}`">

    <!-- Header -->
    <header class="rm-header">
      <span class="rm-logo">Random Meme</span>
      <span v-if="isLoading" class="rm-status rm-status--loading"><span class="rm-dot" /></span>
      <span v-else-if="error" class="rm-status rm-status--error" :title="error">!</span>
      <span v-else-if="currentSubreddit" class="rm-subreddit">r/{{ currentSubreddit }}</span>
    </header>

    <!-- Systemzustände -->
    <div v-if="error"          class="rm-empty">Meme nicht verfügbar</div>
    <div v-else-if="isLoading" class="rm-empty">Lädt…</div>
    <div v-else-if="!visibleMemes.length" class="rm-empty">Kein Meme</div>

    <!-- Grid -->
    <Transition name="rm-fade" mode="out-in">
      <div
        v-if="visibleMemes.length"
        :key="visibleMemes.map(m => m.image_url).join()"
        class="rm-grid"
        :class="`rm-grid--${visibleCount}`"
      >
        <div
          v-for="meme in visibleMemes"
          :key="meme.image_url"
          class="rm-cell"
        >
          <img
            :src="resolveUrl(meme)"
            :alt="meme.title"
            class="rm-image"
            @error="onImageError"
          />
        </div>
      </div>
    </Transition>

  </div>
</template>

<style scoped>
/* ── Variablen & Container ─────────────────────────── */
.rm-widget {
  --c-bg:     #111;
  --c-border: rgba(255, 255, 255, 0.07);
  --c-text:   #e8e8e8;
  --c-muted:  #666;
  --font-ui:  'DM Mono', 'Courier New', monospace;

  width: 100%;
  height: 100%;
  background: var(--c-bg);
  color: var(--c-text);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
  user-select: none;
}

/* ── Header ────────────────────────────────────────── */
.rm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.rm-logo {
  font-family: var(--font-ui);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #fff;
  opacity: 0.9;
}

.rm-subreddit {
  font-family: var(--font-ui);
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--c-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 50%;
}

.rm-status {
  font-family: var(--font-ui);
  font-size: 10px;
  color: var(--c-muted);
}

.rm-status--error { color: #c0392b; font-weight: 700; }

.rm-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  background: var(--c-muted);
  border-radius: 50%;
  animation: rm-pulse 1.4s ease-in-out infinite;
}

@keyframes rm-pulse {
  0%, 100% { opacity: 0.3; }
  50%       { opacity: 1;   }
}

/* ── Leer / Fehler ─────────────────────────────────── */
.rm-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-ui);
  font-size: 11px;
  color: var(--c-muted);
  letter-spacing: 0.08em;
}

/* ── Grid ──────────────────────────────────────────── */
.rm-grid {
  flex: 1;
  display: grid;
  gap: 2px;
  overflow: hidden;
  min-height: 0;
  background: #000;
}

/* 2 Memes nebeneinander (small + large) */
.rm-grid--2 {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr;
}

/* 4 Memes nebeneinander (medium) */
.rm-grid--4 {
  grid-template-columns: repeat(4, 1fr);
  grid-template-rows: 1fr;
}

/* ── Einzelne Zelle ────────────────────────────────── */
.rm-cell {
  overflow: hidden;
  background: #000;
  min-height: 0;
  min-width: 0;
}

/* ── Bild ──────────────────────────────────────────── */
.rm-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

/* ── Fade-Transition ───────────────────────────────── */
.rm-fade-enter-active,
.rm-fade-leave-active {
  transition: opacity 0.35s ease;
}

.rm-fade-enter-from,
.rm-fade-leave-to {
  opacity: 0;
}
</style>
