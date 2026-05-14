<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'
import type { Ref } from 'vue'
import type { CellSize } from '../../composables/useWidgetResize.ts'

// ─── Config ──────────────────────────────────────────────────────────────────
// Hier zentral anpassen, was das Widget anzeigen soll.

const config = {
  ressort: undefined as Ressort | undefined,  // undefined = kein Filter
  regions: [1] as number[],                    // Leeres Array = kein Filter
  //  1=Baden-Württemberg  2=Bayern         3=Berlin        4=Brandenburg
  //  5=Bremen             6=Hamburg        7=Hessen        8=Mecklenburg-Vorpommern
  //  9=Niedersachsen      10=NRW           11=Rheinland-Pfalz 12=Saarland
  //  13=Sachsen           14=Sachsen-Anhalt 15=Schleswig-Holstein 16=Thüringen
  maxItems: { small: 4, medium: 5, large: 6 },
  refreshIntervalMs: 3_600_000,
}

// ─── API Layer ────────────────────────────────────────────────────────────────
// Alles zwischen diesen Kommentaren kann 1:1 durch einen Backend-Call ersetzt
// werden (z.B. fetch('/api/news')), ohne den Rest der Komponente anzufassen.

type Ressort = 'inland' | 'ausland' | 'wirtschaft' | 'sport' | 'video' | 'investigativ' | 'wissen'

interface NewsItem {
  sophoraId: string
  title: string
  topline: string
  firstSentence: string
  date: string
  shareURL: string
  detailsweb: string
  ressort?: string
  breakingNews?: boolean
  teaserImage?: {
    imageVariants?: Record<string, string>
    alttext?: string
  }
}

async function fetchNews(options?: {
  ressort?: Ressort
  regions?: number[]
}): Promise<NewsItem[]> {
  const params = new URLSearchParams()
  if (options?.ressort) params.set('ressort', options.ressort)
  if (options?.regions?.length) params.set('regions', options.regions.join(','))

  const base = 'https://www.tagesschau.de/api2u/news/'
  const url = params.toString() ? `${base}?${params}` : base
  const proxy = `https://corsproxy.io/?${encodeURIComponent(url)}`

  const res = await fetch(proxy)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)

  const parsed = await res.json()
  return (parsed.news ?? []) as NewsItem[]
}

// ─── Component Logic ──────────────────────────────────────────────────────────

// Größe aus Grid-Kontext ableiten
const cellId   = inject<number>('cellId', 0)
const cellSizes = inject<Ref<Record<number, CellSize>>>('cellSizes', ref({}))

const size = computed(() => {
  switch (cellSizes.value[cellId]) {
    case 4:  return 'large'
    case 2:  return 'medium'
    default: return 'small'
  }
})

const news     = ref<NewsItem[]>([])
const isLoading = ref(true)
const error    = ref<string | null>(null)
let intervalId: ReturnType<typeof setInterval> | null = null

const visibleNews = computed(() =>
    news.value.slice(0, config.maxItems[size.value])
)

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

function getImage(item: NewsItem): string | null {
  const variants = item.teaserImage?.imageVariants
  if (!variants) return null
  // bevorzuge mittlere Auflösung
  return (
      variants['16x9-960'] ??
      variants['16x9-640'] ??
      variants['16x9-480'] ??
      Object.values(variants)[0] ??
      null
  )
}

function openArticle(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

async function load() {
  try {
    isLoading.value = true
    error.value = null
    news.value = await fetchNews({ ressort: config.ressort, regions: config.regions })
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Fehler beim Laden'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  load()
  intervalId = setInterval(load, config.refreshIntervalMs)
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
      <span v-if="isLoading" class="ts-status ts-status--loading">
        <span class="ts-dot" />
      </span>
      <span v-else-if="error" class="ts-status ts-status--error" :title="error">!</span>
      <span v-else class="ts-status ts-status--ok">{{ formatDate(new Date().toISOString()) }}</span>
    </header>

    <!-- News List -->
    <ul v-if="!error && visibleNews.length" class="ts-list">
      <li
          v-for="item in visibleNews"
          :key="item.sophoraId"
          class="ts-item"
          :class="{ 'ts-item--breaking': item.breakingNews }"
          @click="openArticle(item.shareURL)"
      >

        <!-- LARGE: Bild oben -->
        <div v-if="size === 'large' && getImage(item)" class="ts-image-wrap">
          <img :src="getImage(item)!" :alt="item.teaserImage?.alttext ?? item.title" class="ts-image" />
          <span v-if="item.breakingNews" class="ts-breaking-badge">Eilmeldung</span>
        </div>

        <div class="ts-content">
          <!-- Topline -->
          <span v-if="item.topline" class="ts-topline">{{ item.topline }}</span>

          <!-- Titel -->
          <p class="ts-title">{{ item.title }}</p>

          <!-- firstSentence + Meta: nur medium & large -->
          <template v-if="size !== 'small'">
            <p v-if="item.firstSentence" class="ts-teaser">{{ item.firstSentence }}</p>
            <div class="ts-meta">
              <span v-if="item.ressort" class="ts-ressort">{{ item.ressort }}</span>
              <span v-if="item.date" class="ts-time">{{ formatDate(item.date) }}</span>
            </div>
          </template>
        </div>

      </li>
    </ul>

    <!-- Fehlerzustand -->
    <div v-else-if="error" class="ts-empty">Nachrichten nicht verfügbar</div>
    <div v-else-if="isLoading" class="ts-empty">Lädt…</div>
    <div v-else class="ts-empty">Keine Meldungen</div>

  </div>
</template>

<style scoped>
/* ── Reset & Container ─────────────────────────────── */
.ts-widget {
  --c-bg:       #111;
  --c-surface:  #1a1a1a;
  --c-border:   rgba(255,255,255,0.07);
  --c-text:     #e8e8e8;
  --c-muted:    #666;
  --c-topline:  #999;
  --c-breaking: #c0392b;
  --c-logo:     #fff;
  --radius:     4px;
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
}

/* ── Header ────────────────────────────────────────── */
.ts-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px 8px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.ts-logo {
  font-family: var(--font-ui);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--c-logo);
  opacity: 0.9;
}

.ts-status {
  font-family: var(--font-ui);
  font-size: 10px;
  color: var(--c-muted);
}

.ts-status--error {
  color: var(--c-breaking);
  font-weight: 700;
}

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

/* ── List ──────────────────────────────────────────── */
.ts-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  flex: 1;
  scrollbar-width: none;
}
.ts-list::-webkit-scrollbar { display: none; }

/* ── Item ──────────────────────────────────────────── */
.ts-item {
  cursor: pointer;
  border-bottom: 1px solid var(--c-border);
  transition: background 0.15s ease;
}

.ts-item:last-child { border-bottom: none; }

.ts-item:hover {
  background: var(--c-surface);
}

/* Breaking-News-Akzent: linke rote Linie */
.ts-item--breaking {
  border-left: 2px solid var(--c-breaking);
}

/* ── Image (large only) ────────────────────────────── */
.ts-image-wrap {
  position: relative;
  width: 100%;
  overflow: hidden;
}

.ts-image {
  width: 100%;
  display: block;
  object-fit: cover;
  max-height: 130px;
  filter: brightness(0.88) saturate(0.7);
  transition: filter 0.2s ease;
}

.ts-item:hover .ts-image {
  filter: brightness(0.95) saturate(0.85);
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

/* ── Content ───────────────────────────────────────── */
.ts-content {
  padding: 9px 14px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.ts-topline {
  font-family: var(--font-ui);
  font-size: 9px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--c-topline);
}

.ts-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--c-text);
}

.ts-teaser {
  margin: 2px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--c-muted);
  font-family: var(--font-ui);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ts-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.ts-ressort {
  font-family: var(--font-ui);
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--c-muted);
  border: 1px solid var(--c-border);
  padding: 1px 5px;
  border-radius: var(--radius);
}

.ts-time {
  font-family: var(--font-ui);
  font-size: 9px;
  color: var(--c-muted);
}

/* ── Empty / Error ─────────────────────────────────── */
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

/* ── Size-spezifische Anpassungen ──────────────────── */

/* small: sehr kompakt */
.ts-widget--small .ts-header {
  padding: 7px 10px 6px;
}
.ts-widget--small .ts-logo {
  font-size: 10px;
}
.ts-widget--small .ts-content {
  padding: 7px 10px;
  gap: 2px;
}
.ts-widget--small .ts-title {
  font-size: 11.5px;
  -webkit-line-clamp: 2;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ts-widget--small .ts-topline {
  font-size: 8px;
}

/* medium: standard */
.ts-widget--medium .ts-title {
  font-size: 12.5px;
}

/* large: mehr Luft, größere Schrift */
.ts-widget--large .ts-header {
  padding: 12px 16px 10px;
}
.ts-widget--large .ts-content {
  padding: 10px 16px 12px;
  gap: 5px;
}
.ts-widget--large .ts-title {
  font-size: 14px;
}
.ts-widget--large .ts-teaser {
  font-size: 12px;
  -webkit-line-clamp: 3;
}
.ts-widget--large .ts-image {
  max-height: 160px;
}
</style>