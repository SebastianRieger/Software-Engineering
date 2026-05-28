<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'
import type { Ref } from 'vue'
import type { CellSize } from '../../composables/useWidgetResize.ts'
import { loadAppConfig } from '../../composables/useAppConfig.ts'
import { getNews } from '../../services/news.ts'
import type { AppConfig } from '../../types/appConfig.ts'
import type { NewsItem } from '../../types/news.ts'

const cellId    = inject<number>('cellId', 0)
const cellSizes = inject<Ref<Record<number, CellSize>>>('cellSizes', ref({}))

const size = computed(() => {
  switch (cellSizes.value[cellId]) {
    case 4:  return 'large'
    case 2:  return 'medium'
    default: return 'small'
  }
})

const news      = ref<NewsItem[]>([])
const isLoading = ref(true)
const error     = ref<string | null>(null)
let intervalId: ReturnType<typeof setInterval> | null = null

// small: 2 | medium: 4 (horizontale Zeilen) | large: 2 (mit Bildern)
const visibleNews = computed(() =>
  news.value.slice(0, size.value === 'medium' ? 4 : 2)
)

function formatDate(iso: string): string {
  return new Date(iso).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

function getImage(item: NewsItem): string | null {
  const v = item.teaserImage?.imageVariants
  if (!v) return null
  return v['16x9-960'] ?? v['16x9-640'] ?? v['16x9-480'] ?? Object.values(v)[0] ?? null
}

async function load(appConfig?: AppConfig) {
  try {
    isLoading.value = true
    error.value = null
    const resolvedConfig = appConfig ?? await loadAppConfig()
    const newsConfig = resolvedConfig.widgets.news
    const response = await getNews({
      ressort: newsConfig.ressort,
      regions: newsConfig.regions,
    })
    news.value = response.news
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Fehler beim Laden'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  void loadAppConfig().then((appConfig) => {
    void load(appConfig)
    intervalId = setInterval(() => {
      void load(appConfig)
    }, appConfig.widgets.news.refresh_seconds * 1000)
  })
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})
</script>

<template>
  <div class="ts-widget" :class="`ts-widget--${size}`">

    <!-- Header -->
    <header class="ts-header">
      <span class="ts-logo">tagesschau</span>
      <span v-if="isLoading" class="ts-status ts-status--loading"><span class="ts-dot" /></span>
      <span v-else-if="error" class="ts-status ts-status--error" :title="error">!</span>
      <span v-else class="ts-status">{{ formatDate(new Date().toISOString()) }}</span>
    </header>

    <!-- Systemzustände -->
    <div v-if="error" class="ts-empty">Nachrichten nicht verfügbar</div>
    <div v-else-if="isLoading" class="ts-empty">Lädt…</div>
    <div v-else-if="!visibleNews.length" class="ts-empty">Keine Meldungen</div>

    <!-- SMALL: 2 Meldungen, kompakte Liste -->
    <ul v-else-if="size === 'small'" class="ts-list">
      <li
        v-for="item in visibleNews"
        :key="item.sophoraId"
        class="ts-item"
        :class="{ 'ts-item--breaking': item.breakingNews }"
      >
        <span v-if="item.topline" class="ts-topline">{{ item.topline }}</span>
        <p class="ts-title">{{ item.title }}</p>
      </li>
    </ul>

    <!-- MEDIUM: 3 horizontale Zeilen mit Badge + Titel + Teaser -->
    <div v-else-if="size === 'medium'" class="ts-rows">
      <div
        v-for="item in visibleNews"
        :key="item.sophoraId"
        class="ts-row"
        :class="{ 'ts-row--breaking': item.breakingNews }"
      >
        <span class="ts-badge">{{ item.ressort ?? item.topline ?? '—' }}</span>
        <div class="ts-row-text">
          <p class="ts-title">{{ item.title }}</p>
        </div>
      </div>
    </div>

    <!-- LARGE: 2 Meldungen mit Bild -->
    <div v-else-if="size === 'large'" class="ts-large-grid">
      <div
        v-for="item in visibleNews"
        :key="item.sophoraId"
        class="ts-large-card"
        :class="{ 'ts-large-card--breaking': item.breakingNews }"
      >
        <div class="ts-image-wrap">
          <img
            v-if="getImage(item)"
            :src="getImage(item)!"
            :alt="item.teaserImage?.alttext ?? item.title"
            class="ts-image"
          />
          <div v-else class="ts-image-placeholder" />
          <span v-if="item.breakingNews" class="ts-breaking-badge">Eilmeldung</span>
        </div>
        <div class="ts-content">
          <span v-if="item.topline" class="ts-topline">{{ item.topline }}</span>
          <p class="ts-title ts-title--large">{{ item.title }}</p>
          <p v-if="item.firstSentence" class="ts-teaser ts-teaser--large">{{ item.firstSentence }}</p>
          <div class="ts-meta">
            <span v-if="item.ressort" class="ts-ressort">{{ item.ressort }}</span>
            <span v-if="item.date" class="ts-time">{{ formatDate(item.date) }}</span>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* ── Variablen & Container ─────────────────────────── */
.ts-widget {
  --c-bg:       #111;
  --c-surface:  #1a1a1a;
  --c-border:   rgba(255,255,255,0.07);
  --c-text:     #e8e8e8;
  --c-muted:    #666;
  --c-topline:  #999;
  --c-breaking: #c0392b;
  --font-head:  'Georgia', 'Times New Roman', serif;
  --font-ui:    'DM Mono', 'Courier New', monospace;

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
.ts-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.ts-logo {
  font-family: var(--font-ui);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #fff;
  opacity: 0.9;
}

.ts-status {
  font-family: var(--font-ui);
  font-size: 10px;
  color: var(--c-muted);
}

.ts-status--error { color: var(--c-breaking); font-weight: 700; }

.ts-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  background: var(--c-muted);
  border-radius: 50%;
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.3; }
  50%       { opacity: 1; }
}

/* ── Leer / Fehler ─────────────────────────────────── */
.ts-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-ui);
  font-size: 11px;
  color: var(--c-muted);
  letter-spacing: 0.08em;
}

/* ── SMALL: 2 Meldungen als Liste ──────────────────── */
.ts-list {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ts-item {
  flex: 1;
  padding: 5px 8px;
  border-bottom: 1px solid var(--c-border);
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.ts-item:last-child { border-bottom: none; }

.ts-item--breaking { border-left: 2px solid var(--c-breaking); }

/* ── MEDIUM: Horizontale Zeilen ────────────────────── */
.ts-rows {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ts-row {
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 12px;
  border-bottom: 1px solid var(--c-border);
  overflow: hidden;
  min-height: 0;
}

.ts-row:last-child { border-bottom: none; }

.ts-row--breaking { border-left: 2px solid var(--c-breaking); }

.ts-badge {
  font-family: var(--font-ui);
  font-size: 8px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--c-muted);
  border: 1px solid var(--c-border);
  padding: 2px 6px;
  border-radius: 2px;
  flex-shrink: 0;
  white-space: nowrap;
  max-width: 72px;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 1px;
}

.ts-row-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  overflow: hidden;
}

.ts-widget--medium .ts-title {
  font-size: 12px;
  line-height: 1.35;
  -webkit-line-clamp: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

/* ── LARGE: 2 Karten nebeneinander mit Bild ────────── */
.ts-large-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 10px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.ts-large-card {
  display: flex;
  flex-direction: column;
  background: var(--c-surface);
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--c-border);
  min-height: 0;
}

.ts-large-card--breaking { border-left: 3px solid var(--c-breaking); }

.ts-image-wrap {
  position: relative;
  flex: 0 0 50%;
  overflow: hidden;
}

.ts-image {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  filter: brightness(0.85) saturate(0.65);
}

.ts-image-placeholder {
  width: 100%;
  height: 100%;
  background: var(--c-surface);
}

.ts-breaking-badge {
  position: absolute;
  bottom: 6px;
  left: 8px;
  background: var(--c-breaking);
  color: #fff;
  font-family: var(--font-ui);
  font-size: 9px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 2px;
}

.ts-content {
  flex: 1;
  padding: 9px 11px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  overflow: hidden;
  min-height: 0;
}

/* ── Gemeinsame Text-Elemente ──────────────────────── */
.ts-topline {
  font-family: var(--font-ui);
  font-size: 8px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--c-topline);
  flex-shrink: 0;
  line-height: 1.3;
}

.ts-title {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--c-text);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ts-title--large {
  font-size: 13px;
  line-height: 1.35;
  -webkit-line-clamp: 2;
}

.ts-teaser {
  margin: 0;
  font-size: 10px;
  line-height: 1.4;
  color: var(--c-muted);
  font-family: var(--font-ui);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ts-teaser--large {
  font-size: 11px;
  line-height: 1.45;
  -webkit-line-clamp: 2;
}

.ts-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 4px;
}

.ts-ressort {
  font-family: var(--font-ui);
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--c-muted);
  border: 1px solid var(--c-border);
  padding: 1px 5px;
  border-radius: 2px;
}

.ts-time {
  font-family: var(--font-ui);
  font-size: 9px;
  color: var(--c-muted);
}
</style>
