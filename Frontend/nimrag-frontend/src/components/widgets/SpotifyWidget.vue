<script setup lang="ts">
import { computed, inject, onBeforeUnmount, onMounted, ref } from 'vue'
import type { Ref } from 'vue'
import type { CellSize } from '../../composables/useWidgetResize'
import { getAuthStatus, getNowPlaying } from '../../services/spotify'
import type { NowPlayingResponse } from '../../types/spotify'

const cellId    = inject<number>('cellId', 0)
const cellSizes = inject<Ref<Record<number, CellSize>>>('cellSizes', ref({}))

const size = computed(() => {
  switch (cellSizes.value[cellId]) {
    case 4:  return 'large'
    case 2:  return 'medium'
    default: return 'small'
  }
})

const data            = ref<NowPlayingResponse | null>(null)
const isLoading       = ref(true)
const error           = ref<string | null>(null)
const localProgressMs = ref(0)
let lastFetchAt       = 0
let fetchTimer: number | null = null
let tickTimer:  number | null = null
let hasAutoOpened     = false

const FETCH_TIMEOUT_MS = 6000

function withTimeout<T>(promise: Promise<T>): Promise<T> {
  return Promise.race([
    promise,
    new Promise<never>((_, reject) =>
      window.setTimeout(() => reject(new Error('timeout')), FETCH_TIMEOUT_MS),
    ),
  ])
}

async function fetchNowPlaying(): Promise<void> {
  try {
    const result = await withTimeout(getNowPlaying())
    data.value            = result
    localProgressMs.value = result.track?.progress_ms ?? 0
    lastFetchAt           = Date.now()
    error.value           = null
  } catch (e: unknown) {
    const status = (e as { status?: number }).status
    if (status === 401 && !hasAutoOpened) {
      hasAutoOpened = true
      try {
        const auth = await getAuthStatus()
        if (auth.auth_url) window.open(auth.auth_url, '_blank')
      } catch { /* ignorieren */ }
    }
    error.value = status === 401 ? 'auth' : 'error'
    data.value  = null
  } finally {
    isLoading.value = false
  }
}

function tick(): void {
  if (!data.value?.is_playing || !data.value.track) return
  localProgressMs.value = Math.min(
    data.value.track.progress_ms + (Date.now() - lastFetchAt),
    data.value.track.duration_ms,
  )
}

const progressPercent = computed(() => {
  const duration = data.value?.track?.duration_ms ?? 0
  if (!duration) return 0
  return Math.min(100, (localProgressMs.value / duration) * 100)
})

const coverUrl = computed(() => data.value?.track?.album_cover_url ?? null)

const bgStyle = computed(() =>
  coverUrl.value ? { backgroundImage: `url("${coverUrl.value}")` } : {},
)

function fmt(ms: number): string {
  const s   = Math.floor(ms / 1000)
  const min = Math.floor(s / 60)
  const sec = s % 60
  return `${min}:${String(sec).padStart(2, '0')}`
}

onMounted(() => {
  void fetchNowPlaying()
  fetchTimer = window.setInterval(() => void fetchNowPlaying(), 5000)
  tickTimer  = window.setInterval(tick, 1000)
})

onBeforeUnmount(() => {
  if (fetchTimer !== null) window.clearInterval(fetchTimer)
  if (tickTimer  !== null) window.clearInterval(tickTimer)
})
</script>

<template>
  <div class="sp-widget" :class="`sp-widget--${size}`">

    <!-- Blurred cover background -->
    <div v-if="coverUrl" class="sp-bg" :style="bgStyle" />
    <div class="sp-overlay" />

    <!-- ── HEADER ─────────────────────────────── -->
    <header class="sp-header sp-layer">
      <div class="sp-brand">
        <svg class="sp-logo" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
        </svg>
        <span class="sp-label">spotify</span>
      </div>
      <div class="sp-header-right">
        <span v-if="isLoading" class="sp-dot-wrap"><span class="sp-dot" /></span>
        <span v-else-if="error" class="sp-err-badge">!</span>
        <template v-else-if="data?.track">
          <span v-if="size !== 'small'" class="sp-time-header">
            {{ fmt(localProgressMs) }}
          </span>
          <svg v-if="data.is_playing" class="sp-state-icon" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6"  y="4" width="4" height="16" rx="1.5" />
            <rect x="14" y="4" width="4" height="16" rx="1.5" />
          </svg>
          <svg v-else class="sp-state-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z" />
          </svg>
        </template>
      </div>
    </header>

    <!-- ── IDLE / ERROR ───────────────────────── -->
    <div v-if="error || isLoading || !data?.track" class="sp-idle sp-layer">
      <div v-if="isLoading" class="sp-idle-ring" />
      <template v-else-if="error">
        <svg class="sp-idle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="13"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <span class="sp-idle-text">{{ error === 'auth' ? 'Nicht verbunden' : 'Keine Verbindung' }}</span>
      </template>
      <template v-else>
        <svg class="sp-idle-icon" viewBox="0 0 24 24" fill="currentColor" opacity="0.4">
          <path d="M8 5v14l11-7z" />
        </svg>
        <span class="sp-idle-text">Pausiert</span>
      </template>
    </div>

    <!-- ── CONTENT ────────────────────────────── -->
    <template v-else-if="data?.track">

      <!-- SMALL: Cover links, Info rechts -->
      <div v-if="size === 'small'" class="sp-small sp-layer">
        <img
          v-if="coverUrl"
          class="sp-small-cover"
          :src="coverUrl"
          :alt="data.track.album"
        />
        <div v-else class="sp-small-cover sp-small-cover--fallback">♫</div>
        <div class="sp-small-info">
          <span class="sp-small-track">{{ data.track.track_name }}</span>
          <span class="sp-small-artist">{{ data.track.artist }}</span>
        </div>
      </div>

      <!-- MEDIUM / LARGE: Links 1x1-Stil, Rechts Warteschlange -->
      <div v-else class="sp-split sp-layer">

        <!-- Linke Hälfte: aktueller Track wie 1x1 -->
        <div class="sp-split-current">
          <img
            v-if="coverUrl"
            class="sp-split-cover"
            :src="coverUrl"
            :alt="data.track.album"
          />
          <div v-else class="sp-split-cover sp-split-cover--fallback">♫</div>
          <div class="sp-split-info">
            <span class="sp-split-track">{{ data.track.track_name }}</span>
            <span class="sp-split-artist">{{ data.track.artist }}</span>
          </div>
        </div>

        <!-- Trennlinie -->
        <div class="sp-split-divider" />

        <!-- Rechte Hälfte: Warteschlange -->
        <div class="sp-split-queue">
          <span class="sp-queue-label">Warteschlange</span>
          <template v-if="data.queue.length > 0">
            <div
              v-for="(item, i) in data.queue.slice(0, size === 'large' ? 3 : 2)"
              :key="i"
              class="sp-queue-item"
            >
              <span class="sp-queue-num">{{ i + 1 }}</span>
              <img
                v-if="item.album_cover_url"
                class="sp-queue-cover"
                :src="item.album_cover_url"
                :alt="item.album"
              />
              <div v-else class="sp-queue-cover sp-queue-cover--fallback">♫</div>
              <div class="sp-queue-info">
                <span class="sp-queue-track">{{ item.track_name }}</span>
                <span class="sp-queue-artist">{{ item.artist }}</span>
              </div>
            </div>
          </template>
          <span v-else class="sp-queue-empty">Leer</span>
        </div>

      </div>

      <!-- Fortschrittsbalken -->
      <div class="sp-progress-wrap sp-layer">
        <span v-if="size !== 'small'" class="sp-time">{{ fmt(localProgressMs) }}</span>
        <div class="sp-bar">
          <div class="sp-bar-fill" :style="{ width: `${progressPercent}%` }" />
        </div>
        <span v-if="size !== 'small'" class="sp-time sp-time--right">{{ fmt(data.track.duration_ms) }}</span>
      </div>

    </template>

  </div>
</template>

<style scoped>
/* ── Shell ── */
.sp-widget {
  --green:   #1db954;
  --font:    'DM Mono', 'Courier New', monospace;
  --text:    #fff;
  --muted:   rgba(255,255,255,0.5);
  --border:  rgba(255,255,255,0.10);

  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #0d0d0d;
  color: var(--text);
  font-family: var(--font);
  user-select: none;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

/* ── Blurred background ── */
.sp-bg {
  position: absolute;
  inset: -24px;
  background-size: cover;
  background-position: center;
  filter: blur(28px);
  transform: scale(1.08);
  opacity: 0.45;
  z-index: 0;
  transition: background-image 0.8s ease;
}

.sp-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(0,0,0,0.72) 0%,
    rgba(0,0,0,0.52) 40%,
    rgba(0,0,0,0.78) 100%
  );
  z-index: 1;
}

.sp-layer {
  position: relative;
  z-index: 2;
}

/* ── Header ── */
.sp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px 6px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  backdrop-filter: blur(4px);
}

.sp-brand {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sp-logo {
  width: 13px;
  height: 13px;
  color: var(--green);
  flex-shrink: 0;
}

.sp-label {
  font-size: 14px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--text);
  opacity: 0.85;
}

.sp-header-right {
  display: flex;
  align-items: center;
  gap: 7px;
}

.sp-time-header {
  font-size: 14px;
  color: var(--muted);
  letter-spacing: 0.05em;
}

.sp-state-icon {
  width: 13px;
  height: 13px;
  color: var(--green);
}

.sp-dot-wrap { display: flex; align-items: center; }

.sp-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  background: var(--muted);
  border-radius: 50%;
  animation: sp-pulse 1.4s ease-in-out infinite;
}

@keyframes sp-pulse {
  0%, 100% { opacity: 0.25; }
  50%       { opacity: 1; }
}

.sp-err-badge {
  font-size: 12px;
  font-weight: 700;
  color: #e74c3c;
}

/* ── Idle / Error / Pause ── */
.sp-idle {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding-bottom: 8px;
}

.sp-idle-ring {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid rgba(255,255,255,0.12);
  border-top-color: var(--green);
  animation: spin 0.9s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.sp-idle-icon {
  width: 28px;
  height: 28px;
  color: var(--muted);
}

.sp-idle-text {
  font-size: 15px;
  color: var(--muted);
  letter-spacing: 0.1em;
}

/* ── SMALL layout ── */
.sp-small {
  flex: 1;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  padding: 8px 10px 4px;
  min-height: 0;
  overflow: hidden;
}

.sp-small-cover {
  height: calc(100% - 8px);
  max-height: 120px;
  width: auto;
  aspect-ratio: 1;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
  box-shadow: 0 4px 16px rgba(0,0,0,0.6);
}

.sp-small-cover--fallback {
  background: rgba(255,255,255,0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  color: var(--muted);
  border: 1px solid var(--border);
}

.sp-small-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
  overflow: hidden;
}

.sp-small-track {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0 1px 6px rgba(0,0,0,0.8);
  letter-spacing: 0.01em;
  line-height: 1.2;
}

.sp-small-artist {
  font-size: 14px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

/* ── MEDIUM / LARGE split layout ── */
.sp-split {
  flex: 1;
  display: flex;
  flex-direction: row;
  min-height: 0;
  overflow: hidden;
}

/* Linke Hälfte: Cover links, Text rechts */
.sp-split-current {
  width: 50%;
  flex-shrink: 0;
  align-self: stretch;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  overflow: hidden;
}

.sp-split-cover {
  height: calc(100% - 8px);
  max-height: 160px;
  width: auto;
  aspect-ratio: 1;
  border-radius: 8px;
  object-fit: cover;
  box-shadow: 0 6px 20px rgba(0,0,0,0.7);
  flex-shrink: 0;
}

.sp-split-cover--fallback {
  background: rgba(255,255,255,0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.8rem;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 8px;
  height: calc(100% - 8px);
  max-height: 160px;
  aspect-ratio: 1;
}

.sp-split-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
  overflow: hidden;
}

.sp-split-track {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0 1px 6px rgba(0,0,0,0.8);
  line-height: 1.2;
}

.sp-widget--large .sp-split-track { font-size: 19px; }

.sp-split-artist {
  font-size: 14px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

.sp-widget--large .sp-split-artist { font-size: 16px; }

/* Trennlinie */
.sp-split-divider {
  width: 1px;
  background: var(--border);
  flex-shrink: 0;
  margin: 10px 0;
}

/* Rechte Hälfte: Queue */
.sp-split-queue {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 2px;
  padding: 10px 10px 8px;
  overflow: hidden;
  min-width: 0;
}

/* ── Queue ── */
.sp-queue-label {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.25);
  margin-bottom: 4px;
  flex-shrink: 0;
}

.sp-queue-empty {
  font-size: 12px;
  color: rgba(255,255,255,0.2);
  letter-spacing: 0.06em;
}

.sp-queue {
  display: flex;
  flex-direction: column;
  gap: 1px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

.sp-queue-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 4px 0;
  min-height: 0;
  overflow: hidden;
}

.sp-queue-num {
  font-size: 13px;
  color: rgba(255,255,255,0.2);
  min-width: 14px;
  text-align: right;
  flex-shrink: 0;
}

.sp-queue-cover {
  height: 100%;
  max-height: 52px;
  width: auto;
  aspect-ratio: 1;
  border-radius: 4px;
  object-fit: cover;
  flex-shrink: 0;
  opacity: 0.85;
}

.sp-queue-cover--fallback {
  background: rgba(255,255,255,0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  color: var(--muted);
  border: 1px solid var(--border);
  height: 100%;
  max-height: 52px;
  aspect-ratio: 1;
  border-radius: 4px;
}

.sp-queue-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
  overflow: hidden;
}

.sp-queue-track {
  font-size: 15px;
  font-weight: 600;
  color: rgba(255,255,255,0.65);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

.sp-queue-artist {
  font-size: 13px;
  color: rgba(255,255,255,0.35);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

/* ── Progress bar ── */
.sp-progress-wrap {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 4px 10px 9px;
  flex-shrink: 0;
}

.sp-time {
  font-size: 13px;
  color: var(--muted);
  min-width: 30px;
  flex-shrink: 0;
  letter-spacing: 0.04em;
}

.sp-time--right { text-align: right; }

.sp-bar {
  flex: 1;
  height: 3px;
  background: rgba(255,255,255,0.12);
  border-radius: 2px;
  overflow: hidden;
}

.sp-bar-fill {
  height: 100%;
  background: var(--green);
  border-radius: 2px;
  transition: width 0.9s linear;
  box-shadow: 0 0 6px rgba(29,185,84,0.6);
}

/* Kein Cover → dunkleres Fallback-BG */
.sp-widget:not(:has(.sp-bg)) {
  background: #111;
}
</style>
