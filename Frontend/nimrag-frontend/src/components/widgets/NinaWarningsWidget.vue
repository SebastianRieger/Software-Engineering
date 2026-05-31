<script setup lang="ts">
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Ref } from 'vue'
import type { CellSize } from '../../composables/useWidgetResize'
import { loadAppConfig } from '../../composables/useAppConfig'

const CYCLE_MS = 6000

export interface NinaNormalizedWarning {
  id: string
  severity: string
  headline: string
  sender_name: string
  event: string | null
  sent: string
  msg_type: string
}

const cellId    = inject<number>('cellId', 0)
const cellSizes = inject<Ref<Record<number, CellSize>>>('cellSizes', ref({}))
const cellSize  = computed(() => cellSizes.value[cellId] ?? 1)

const size = computed<'small' | 'medium' | 'large'>(() => {
  switch (cellSize.value) {
    case 4:  return 'large'
    case 2:  return 'medium'
    default: return 'small'
  }
})

const props = defineProps<{
  ars?: string
  refreshInterval?: number
}>()

const warnings = ref<NinaNormalizedWarning[]>([])
const loading  = ref(true)
const error    = ref<string | null>(null)

let effectiveArs       = ''
let effectiveRefreshMs = 300_000
let refreshTimer: number | null = null

async function fetchWarnings(): Promise<void> {
  if (!effectiveArs) return
  loading.value = true
  error.value   = null
  try {
    const response = await fetch(
      `${(import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'}/api/v1/nina/${effectiveArs}`,
    )
    if (!response.ok) {
      error.value    = `Fehler ${response.status}`
      warnings.value = []
      return
    }
    const data     = await response.json()
    warnings.value = data.warnings ?? []
  } catch {
    error.value    = 'Keine Verbindung'
    warnings.value = []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const config       = await loadAppConfig()
  effectiveArs       = props.ars ?? config.widgets.nina?.ars ?? ''
  effectiveRefreshMs = props.refreshInterval ?? (config.widgets.nina?.refresh_seconds ?? 300) * 1000

  if (!effectiveArs) {
    error.value   = 'Kein ARS konfiguriert'
    loading.value = false
    return
  }

  await fetchWarnings()
  refreshTimer = window.setInterval(fetchWarnings, effectiveRefreshMs)
})

onBeforeUnmount(() => {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }
  stopCycle()
})

// Card cycling
const currentIndex = ref(0)
let cycleTimer: number | null = null

function stopCycle(): void {
  if (cycleTimer !== null) {
    window.clearInterval(cycleTimer)
    cycleTimer = null
  }
}

function startCycle(): void {
  stopCycle()
  if (warnings.value.length > 1) {
    cycleTimer = window.setInterval(() => {
      currentIndex.value = (currentIndex.value + 1) % warnings.value.length
    }, CYCLE_MS)
  }
}

watch(warnings, (newWarnings) => {
  if (currentIndex.value >= newWarnings.length) currentIndex.value = 0
  startCycle()
})

const currentWarning = computed<NinaNormalizedWarning | null>(
  () => warnings.value[currentIndex.value] ?? null,
)

type SeverityLevel = 'Extreme' | 'Severe' | 'Moderate' | 'Minor' | 'Unknown'

const SEVERITY_CONFIG: Record<SeverityLevel, { bg: string; label: string }> = {
  Extreme:  { bg: '#dc2626', label: 'EXTREM' },
  Severe:   { bg: '#ea580c', label: 'SCHWER' },
  Moderate: { bg: '#ca8a04', label: 'MITTEL' },
  Minor:    { bg: '#2563eb', label: 'GERING' },
  Unknown:  { bg: '#4b5563', label: 'UNBEKANNT' },
}

function severityConfig(severity: string) {
  return SEVERITY_CONFIG[severity as SeverityLevel] ?? SEVERITY_CONFIG.Unknown
}

const highestSeverity = computed<SeverityLevel>(() => {
  const order: SeverityLevel[] = ['Extreme', 'Severe', 'Moderate', 'Minor', 'Unknown']
  for (const level of order) {
    if (warnings.value.some(w => w.severity === level)) return level
  }
  return 'Unknown'
})

const rootClass = computed(() => ({
  'nina-widget--danger':   highestSeverity.value === 'Extreme' || highestSeverity.value === 'Severe',
  'nina-widget--warnings': highestSeverity.value === 'Minor'   || highestSeverity.value === 'Moderate',
}))

function relativeTime(iso: string): string {
  const diffSec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diffSec < 60)  return `vor ${diffSec} Sek`
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60)  return `vor ${diffMin} Min`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24)    return `vor ${diffH}h`
  return `vor ${Math.floor(diffH / 24)}d`
}

function formatTime(): string {
  return new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

const showLoading  = computed(() => loading.value && warnings.value.length === 0)
const warningCount = computed(() => warnings.value.length)
const countLabel   = computed(() =>
  warningCount.value === 1 ? '1 Warnung' : `${warningCount.value} Warnungen`,
)
</script>

<template>
  <div class="nina-widget" :class="[rootClass, `nina-widget--${size}`]">

    <!-- Header -->
    <header class="nina-header">
      <span class="nina-label">nina</span>
      <div class="nina-header-right">
        <span v-if="size !== 'small' && warnings.length > 0" class="nina-count-badge">
          {{ countLabel }}
        </span>
        <span v-if="loading" class="nina-status nina-status--loading"><span class="nina-dot" /></span>
        <span v-else-if="error" class="nina-status nina-status--error" :title="error ?? ''">!</span>
        <span v-else class="nina-status">{{ formatTime() }}</span>
      </div>
    </header>

    <!-- Lade- / Fehlerzustand -->
    <div v-if="showLoading" class="nina-empty">Lädt…</div>
    <div v-else-if="error && warnings.length === 0" class="nina-empty">{{ error }}</div>

    <!-- Keine Warnungen -->
    <div v-else-if="!loading && warnings.length === 0" class="nina-empty">Keine aktuellen Warnungen</div>

    <!-- ── SMALL (1×1) ── -->
    <template v-else-if="size === 'small'">
      <Transition name="nina-fade" mode="out-in">
        <div v-if="currentWarning" :key="currentWarning.id" class="nina-card nina-card--small">
          <span
            class="nina-badge"
            :style="{ backgroundColor: severityConfig(currentWarning.severity).bg }"
          >{{ severityConfig(currentWarning.severity).label }}</span>
          <p class="nina-headline nina-headline--small">{{ currentWarning.headline }}</p>
          <div v-if="warningCount > 1" class="nina-dots" aria-hidden="true">
            <span
              v-for="(_, i) in warnings" :key="i"
              class="nina-pip" :class="{ 'nina-pip--active': i === currentIndex }"
            />
          </div>
        </div>
      </Transition>
    </template>

    <!-- ── MEDIUM (2×1) ── -->
    <template v-else-if="size === 'medium'">
      <Transition name="nina-fade" mode="out-in">
        <div v-if="currentWarning" :key="currentWarning.id" class="nina-card nina-card--medium">
          <span
            class="nina-badge"
            :style="{ backgroundColor: severityConfig(currentWarning.severity).bg }"
          >{{ severityConfig(currentWarning.severity).label }}</span>
          <div class="nina-body">
            <p class="nina-headline nina-headline--medium">{{ currentWarning.headline }}</p>
            <p class="nina-meta">
              {{ currentWarning.sender_name }}
              <template v-if="currentWarning.event"> · {{ currentWarning.event }}</template>
              <span class="nina-time"> · {{ relativeTime(currentWarning.sent) }}</span>
            </p>
          </div>
          <div v-if="warningCount > 1" class="nina-dots nina-dots--right" aria-hidden="true">
            <span
              v-for="(_, i) in warnings" :key="i"
              class="nina-pip" :class="{ 'nina-pip--active': i === currentIndex }"
            />
          </div>
        </div>
      </Transition>
    </template>

    <!-- ── LARGE (2×2) ── -->
    <template v-else>
      <div class="nina-list">
        <div
          v-for="(w, i) in warnings"
          :key="w.id"
          class="nina-list-row"
          :class="{ 'nina-list-row--active': i === currentIndex }"
        >
          <span
            class="nina-badge"
            :style="{ backgroundColor: severityConfig(w.severity).bg }"
          >{{ severityConfig(w.severity).label }}</span>
          <div class="nina-list-body">
            <p class="nina-headline">{{ w.headline }}</p>
            <p class="nina-meta">
              {{ w.sender_name }}
              <template v-if="w.event"> · {{ w.event }}</template>
            </p>
          </div>
          <span class="nina-time">{{ relativeTime(w.sent) }}</span>
        </div>
      </div>
    </template>

  </div>
</template>

<style scoped>
/* ── Variablen & Container ─────────────────────────── */
.nina-widget {
  --c-bg:       #111;
  --c-surface:  #1a1a1a;
  --c-border:   rgba(255,255,255,0.07);
  --c-text:     #e8e8e8;
  --c-muted:    #666;
  --c-extreme:  #dc2626;
  --c-severe:   #ea580c;
  --c-moderate: #ca8a04;
  --c-minor:    #2563eb;
  --font-ui:    'DM Mono', 'Courier New', monospace;

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
  border: 1px solid transparent;
}

/* ── Danger-Animationen ────────────────────────────── */
@keyframes nina-border-red {
  0%, 100% { border-color: transparent; }
  50%       { border-color: var(--c-extreme); }
}
@keyframes nina-border-amber {
  0%, 100% { border-color: transparent; }
  50%       { border-color: var(--c-moderate); }
}

.nina-widget--danger   { animation: nina-border-red   2.5s ease-in-out infinite; }
.nina-widget--warnings { animation: nina-border-amber  3s  ease-in-out infinite; }

/* ── Header ────────────────────────────────────────── */
.nina-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.nina-label {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #fff;
  opacity: 0.9;
}

.nina-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nina-count-badge {
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--c-muted);
  border: 1px solid var(--c-border);
  padding: 1px 6px;
  border-radius: 2px;
  white-space: nowrap;
}

.nina-status {
  font-size: 10px;
  color: var(--c-muted);
}

.nina-status--error { color: var(--c-extreme); font-weight: 700; }

.nina-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  background: var(--c-muted);
  border-radius: 50%;
  animation: nina-pulse 1.4s ease-in-out infinite;
}

@keyframes nina-pulse {
  0%, 100% { opacity: 0.3; }
  50%       { opacity: 1; }
}

/* ── Leer / Fehler ─────────────────────────────────── */
.nina-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--c-muted);
  letter-spacing: 0.08em;
}

/* ── Gemeinsame Elemente ───────────────────────────── */
.nina-badge {
  display: inline-block;
  flex-shrink: 0;
  padding: 2px 6px;
  border-radius: 2px;
  font-size: 9px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  white-space: nowrap;
}

.nina-headline {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--c-text);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.nina-meta {
  font-size: 11px;
  color: var(--c-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
  letter-spacing: 0.04em;
}

.nina-time {
  font-size: 11px;
  color: var(--c-muted);
  flex-shrink: 0;
  white-space: nowrap;
}

.nina-dots {
  display: flex;
  gap: 3px;
  flex-shrink: 0;
}

.nina-dots--right {
  flex-direction: column;
  gap: 4px;
}

.nina-pip {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--c-muted);
  transition: background 0.2s;
  flex-shrink: 0;
}

.nina-pip--active { background: var(--c-text); }

/* ── SMALL (1×1) ───────────────────────────────────── */
.nina-card--small {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 8px 10px;
  overflow: hidden;
}

.nina-headline--small {
  font-size: 12px;
  -webkit-line-clamp: 3;
}

/* ── MEDIUM (2×1) ──────────────────────────────────── */
.nina-card--medium {
  flex: 1;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  overflow: hidden;
}

.nina-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  overflow: hidden;
}

.nina-headline--medium {
  -webkit-line-clamp: 1;
  white-space: nowrap;
  display: block;
}

/* ── LARGE (2×2) ───────────────────────────────────── */
.nina-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 4px 0;
}

.nina-list-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
  transition: background 0.15s;
}

.nina-list-row:last-child { border-bottom: none; }

.nina-list-row--active { background: var(--c-surface); }

.nina-list-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.nina-list-body .nina-headline {
  -webkit-line-clamp: 1;
  white-space: nowrap;
  display: block;
}

/* ── Fade ──────────────────────────────────────────── */
.nina-fade-enter-active,
.nina-fade-leave-active  { transition: opacity 0.3s ease; }
.nina-fade-enter-from,
.nina-fade-leave-to      { opacity: 0; }
</style>
