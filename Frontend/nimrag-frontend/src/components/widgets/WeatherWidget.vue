<script setup lang="ts">
import { computed, inject, onBeforeUnmount, onMounted, ref } from 'vue'
import type { Ref } from 'vue'
import type { CellSize } from '../../composables/useWidgetResize'
import { loadAppConfig } from '../../composables/useAppConfig'
import { getCurrentWeather, getForecast } from '../../services/weather'
import type { WeatherCurrentResponse, WeatherForecastEntry } from '../../types/weather'

const cellId    = inject<number>('cellId', 0)
const cellSizes = inject<Ref<Record<number, CellSize>>>('cellSizes', ref({}))

const size = computed(() => {
  switch (cellSizes.value[cellId]) {
    case 4:  return 'large'
    case 2:  return 'medium'
    default: return 'small'
  }
})

const current     = ref<WeatherCurrentResponse | null>(null)
const forecastDays = ref<WeatherForecastEntry[]>([])
const isLoading   = ref(true)
const error       = ref<string | null>(null)
let refreshTimer: number | null = null

function conditionEmoji(condition: string): string {
  const c = condition.toLowerCase()
  if (c.includes('thunderstorm'))                      return '⛈️'
  if (c.includes('snow shower') || c.includes('snow grain')) return '🌨️'
  if (c.includes('snow'))                              return '❄️'
  if (c.includes('freezing'))                          return '🌨️'
  if (c.includes('violent rain') || c.includes('heavy rain')) return '⛈️'
  if (c.includes('shower'))                            return '🌦️'
  if (c.includes('rain'))                              return '🌧️'
  if (c.includes('drizzle'))                           return '🌦️'
  if (c.includes('fog'))                               return '🌫️'
  if (c.includes('overcast'))                          return '☁️'
  if (c.includes('partly cloudy'))                     return '⛅'
  if (c.includes('mainly clear'))                      return '🌤️'
  if (c.includes('clear'))                             return '☀️'
  return '🌡️'
}

function formatDay(dateStr: string): string {
  const labels = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']
  const d     = new Date(dateStr + 'T12:00:00')
  const today = new Date()
  if (d.toDateString() === today.toDateString()) return 'Heute'
  const tomorrow = new Date(today)
  tomorrow.setDate(today.getDate() + 1)
  if (d.toDateString() === tomorrow.toDateString()) return 'Morgen'
  return labels[d.getDay()] ?? 'Mo'
}

function formatTime(): string {
  return new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

function isToday(dateStr: string): boolean {
  return new Date(dateStr + 'T12:00:00').toDateString() === new Date().toDateString()
}

async function loadWeather(): Promise<void> {
  isLoading.value = true
  error.value     = null
  try {
    const [cur, fore] = await Promise.all([getCurrentWeather(), getForecast(5)])
    current.value      = cur
    forecastDays.value = fore.forecast
  } catch (e) {
    current.value      = null
    forecastDays.value = []
    error.value        = e instanceof Error ? e.message : 'Wetterdaten nicht verfügbar.'
  } finally {
    isLoading.value = false
  }
}

const locationLabel = computed(() => current.value?.location_name ?? '—')

onMounted(() => {
  void loadAppConfig().then((cfg) => {
    void loadWeather()
    refreshTimer = window.setInterval(
      () => void loadWeather(),
      cfg.widgets.weather.refresh_seconds * 1000,
    )
  })
})

onBeforeUnmount(() => {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<template>
  <div class="wx-widget" :class="`wx-widget--${size}`">

    <!-- Header -->
    <header class="wx-header">
      <span class="wx-label">wetter</span>
      <div class="wx-header-right">
        <span v-if="current" class="wx-loc">{{ locationLabel }}</span>
        <span v-if="isLoading" class="wx-status wx-status--loading"><span class="wx-dot" /></span>
        <span v-else-if="error" class="wx-status wx-status--error" :title="error ?? ''">!</span>
        <span v-else class="wx-status">{{ formatTime() }}</span>
      </div>
    </header>

    <!-- Lade- / Fehlerzustand -->
    <div v-if="error" class="wx-empty">{{ error }}</div>
    <div v-else-if="isLoading" class="wx-empty">Lädt…</div>

    <!-- SMALL: großes Emoji + Temperatur + Condition + Meta -->
    <template v-else-if="size === 'small' && current">
      <div class="wx-current">
        <span class="wx-emoji">{{ conditionEmoji(current.condition) }}</span>
        <div class="wx-current-body">
          <span class="wx-temp">{{ Math.round(current.temperature) }}°</span>
          <span class="wx-condition">{{ current.condition }}</span>
        </div>
      </div>
      <div class="wx-meta">
        <span>💧 {{ Math.round(current.humidity) }}%</span>
        <span>💨 {{ current.wind_speed.toFixed(1) }} m/s</span>
      </div>
    </template>

    <!-- MEDIUM / LARGE: Aktuelles Wetter + 5-Tage-Prognose -->
    <template v-else-if="current">
      <div class="wx-current wx-current--wide">
        <span class="wx-emoji">{{ conditionEmoji(current.condition) }}</span>
        <div class="wx-current-body">
          <span class="wx-temp">{{ Math.round(current.temperature) }}°</span>
          <span class="wx-condition">{{ current.condition }}</span>
        </div>
        <div class="wx-meta wx-meta--right">
          <span>💧 {{ Math.round(current.humidity) }}%</span>
          <span>💨 {{ current.wind_speed.toFixed(1) }} m/s</span>
        </div>
      </div>

      <!-- 5-Tage-Prognose -->
      <div v-if="forecastDays.length" class="wx-forecast">
        <div
          v-for="day in forecastDays"
          :key="day.date"
          class="wx-day"
          :class="{ 'wx-day--today': isToday(day.date) }"
        >
          <span class="wx-day-name">{{ formatDay(day.date) }}</span>
          <span class="wx-day-emoji">{{ conditionEmoji(day.condition) }}</span>
          <span class="wx-day-max">{{ Math.round(day.max_temp) }}°</span>
          <span class="wx-day-min">{{ Math.round(day.min_temp) }}°</span>
        </div>
      </div>
    </template>

  </div>
</template>

<style scoped>
/* ── Variablen & Container ─────────────────────────── */
.wx-widget {
  --c-bg:      #111;
  --c-surface: #1a1a1a;
  --c-border:  rgba(255,255,255,0.07);
  --c-text:    #e8e8e8;
  --c-muted:   #666;
  --font-ui:   'DM Mono', 'Courier New', monospace;

  width: 100%;
  height: 100%;
  background: var(--c-bg);
  color: var(--c-text);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
  font-family: var(--font-ui);
  user-select: none;
}

/* ── Header ────────────────────────────────────────── */
.wx-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.wx-label {
  font-size: 13px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #fff;
  opacity: 0.9;
}

.wx-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.wx-loc {
  font-size: 12px;
  color: var(--c-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 110px;
}

.wx-status {
  font-size: 12px;
  color: var(--c-muted);
}

.wx-status--error { color: #c0392b; font-weight: 700; }

.wx-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  background: var(--c-muted);
  border-radius: 50%;
  animation: wx-pulse 1.4s ease-in-out infinite;
}

@keyframes wx-pulse {
  0%, 100% { opacity: 0.3; }
  50%       { opacity: 1; }
}

/* ── Leer / Fehler ─────────────────────────────────── */
.wx-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--c-muted);
  letter-spacing: 0.08em;
}

/* ── Aktuelles Wetter ──────────────────────────────── */
.wx-current {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px 6px;
  flex-shrink: 0;
}

.wx-current--wide {
  padding-bottom: 8px;
}

.wx-emoji {
  font-size: 2.4rem;
  line-height: 1;
  flex-shrink: 0;
}

.wx-widget--small  .wx-emoji { font-size: 2.1rem; }
.wx-widget--medium .wx-emoji { font-size: 1.9rem; }
.wx-widget--large  .wx-emoji { font-size: 2.8rem; }

.wx-current-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.wx-widget--medium .wx-current-body {
  flex-direction: row;
  align-items: baseline;
  gap: 8px;
}

.wx-temp {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
  color: var(--c-text);
}

.wx-widget--small  .wx-temp { font-size: 1.7rem; }
.wx-widget--medium .wx-temp { font-size: 1.6rem; }
.wx-widget--large  .wx-temp { font-size: 2.5rem; }

.wx-condition {
  font-size: 12px;
  color: var(--c-muted);
  letter-spacing: 0.04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wx-widget--large .wx-condition { font-size: 13px; }

/* ── Meta (Luftfeuchte, Wind) ──────────────────────── */
.wx-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 12px 8px;
  font-size: 12px;
  color: var(--c-muted);
  flex-shrink: 0;
}

.wx-meta--right {
  flex-direction: row;
  align-items: center;
  gap: 10px;
  padding: 0;
  margin-left: auto;
  flex-shrink: 0;
}

/* ── 5-Tage-Prognose ───────────────────────────────── */
.wx-forecast {
  border-top: 1px solid var(--c-border);
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  flex: 1;
  min-height: 0;
}

.wx-day {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 4px;
  border-right: 1px solid var(--c-border);
  transition: background 0.15s;
}

.wx-day:last-child { border-right: none; }

.wx-day--today {
  background: var(--c-surface);
}

.wx-widget--medium .wx-day--today {
  padding: 3px 4px;
  gap: 3px;
}

.wx-day-name {
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--c-muted);
  line-height: 1;
}

.wx-day--today .wx-day-name {
  color: var(--c-text);
}

.wx-day-emoji { font-size: 1.3rem; line-height: 1; }

.wx-widget--large .wx-day-emoji { font-size: 1.6rem; }

.wx-day-max {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
  line-height: 1;
}

.wx-day-min {
  font-size: 12px;
  color: var(--c-muted);
  line-height: 1;
}

.wx-widget--large .wx-day-max { font-size: 15px; }
.wx-widget--large .wx-day-min { font-size: 13px; }
</style>
