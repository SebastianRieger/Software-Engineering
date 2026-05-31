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
// 1 = 1×1 kompakt | 2 = 2×1 breit | 4 = 2×2 voll
const layout = computed<'compact' | 'wide' | 'full'>(() =>
  cellSize.value === 4 ? 'full' : cellSize.value === 2 ? 'wide' : 'compact',
)

const props = defineProps<{
  ars?: string
  refreshInterval?: number
}>()

const warnings = ref<NinaNormalizedWarning[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

let effectiveArs = ''
let effectiveRefreshMs = 300_000
let refreshTimer: number | null = null

async function fetchWarnings(): Promise<void> {
  if (!effectiveArs) return
  loading.value = true
  error.value = null
  try {
    const response = await fetch(
      `${(import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'}/api/v1/nina/${effectiveArs}`,
    )
    if (!response.ok) {
      error.value = `Fehler ${response.status}`
      warnings.value = []
      return
    }
    const data = await response.json()
    warnings.value = data.warnings ?? []
  } catch {
    error.value = 'Keine Verbindung'
    warnings.value = []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const config = await loadAppConfig()
  effectiveArs = props.ars ?? config.widgets.nina?.ars ?? ''
  effectiveRefreshMs = props.refreshInterval ?? (config.widgets.nina?.refresh_seconds ?? 300) * 1000

  if (!effectiveArs) {
    error.value = 'Kein ARS konfiguriert'
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
  if (currentIndex.value >= newWarnings.length) {
    currentIndex.value = 0
  }
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

const showLoading = computed(() => loading.value && warnings.value.length === 0)
const warningCount = computed(() => warnings.value.length)
const countLabel = computed(() =>
  warningCount.value === 1 ? '1 Warnung' : `${warningCount.value} Warnungen`,
)
</script>

<template>
  <div class="nina-widget" :class="[rootClass, `nina-widget--${layout}`]">

    <!-- Loading -->
    <template v-if="showLoading">
      <span class="nina-spinner">🛡</span>
    </template>

    <!-- Error -->
    <template v-else-if="error && warnings.length === 0">
      <span class="nina-icon">⚠️</span>
      <p v-if="layout !== 'compact'" class="nina-error">{{ error }}</p>
    </template>

    <!-- Keine Warnungen -->
    <template v-else-if="!loading && warnings.length === 0">
      <span class="nina-icon">😊</span>
      <p v-if="layout !== 'compact'" class="nina-ok">Keine aktuellen Warnungen</p>
    </template>

    <!-- ── 1×1 kompakt ── -->
    <template v-else-if="layout === 'compact'">
      <Transition name="nina-fade" mode="out-in">
        <div v-if="currentWarning" :key="currentWarning.id" class="nina-card nina-card--compact">
          <span
            class="nina-badge nina-badge--compact"
            :style="{ backgroundColor: severityConfig(currentWarning.severity).bg }"
          >{{ severityConfig(currentWarning.severity).label }}</span>
          <p class="nina-headline nina-headline--compact">{{ currentWarning.headline }}</p>
          <div v-if="warningCount > 1" class="nina-dots nina-dots--compact" aria-hidden="true">
            <span
              v-for="(_, i) in warnings" :key="i"
              class="nina-dot" :class="{ 'nina-dot--active': i === currentIndex }"
            />
          </div>
        </div>
      </Transition>
    </template>

    <!-- ── 2×1 breit ── -->
    <template v-else-if="layout === 'wide'">
      <div class="nina-header">
        <span class="nina-count">{{ countLabel }}</span>
        <span v-if="warningCount > 1" class="nina-dots" aria-hidden="true">
          <span
            v-for="(_, i) in warnings" :key="i"
            class="nina-dot" :class="{ 'nina-dot--active': i === currentIndex }"
          />
        </span>
      </div>
      <Transition name="nina-fade" mode="out-in">
        <div v-if="currentWarning" :key="currentWarning.id" class="nina-card nina-card--wide">
          <span
            class="nina-badge"
            :style="{ backgroundColor: severityConfig(currentWarning.severity).bg }"
          >{{ severityConfig(currentWarning.severity).label }}</span>
          <div class="nina-wide-body">
            <p class="nina-headline nina-headline--wide">{{ currentWarning.headline }}</p>
            <p class="nina-meta">
              {{ currentWarning.sender_name }}
              <template v-if="currentWarning.event"> · {{ currentWarning.event }}</template>
              <span class="nina-time"> · {{ relativeTime(currentWarning.sent) }}</span>
            </p>
          </div>
        </div>
      </Transition>
    </template>

    <!-- ── 2×2 voll ── -->
    <template v-else>
      <div class="nina-header">
        <span class="nina-count">{{ countLabel }}</span>
        <span v-if="warningCount > 1" class="nina-dots" aria-hidden="true">
          <span
            v-for="(_, i) in warnings" :key="i"
            class="nina-dot" :class="{ 'nina-dot--active': i === currentIndex }"
          />
        </span>
      </div>
      <Transition name="nina-fade" mode="out-in">
        <div v-if="currentWarning" :key="currentWarning.id" class="nina-card">
          <span
            class="nina-badge"
            :style="{ backgroundColor: severityConfig(currentWarning.severity).bg }"
          >{{ severityConfig(currentWarning.severity).label }}</span>
          <p class="nina-headline">{{ currentWarning.headline }}</p>
          <p class="nina-meta">
            {{ currentWarning.sender_name }}
            <template v-if="currentWarning.event"> · {{ currentWarning.event }}</template>
          </p>
          <p class="nina-time">{{ relativeTime(currentWarning.sent) }}</p>
        </div>
      </Transition>
    </template>

  </div>
</template>

<style scoped>
.nina-widget {
  width: 100%;
  height: 100%;
  background: #111;
  color: #eee;
  padding: 14px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  border: 2px solid transparent;
  border-radius: 4px;
  overflow: hidden;
}

@keyframes nina-border-red {
  0%, 100% { border-color: transparent; }
  50%       { border-color: #dc2626; }
}
@keyframes nina-border-amber {
  0%, 100% { border-color: transparent; }
  50%       { border-color: #d97706; }
}

.nina-widget--danger   { animation: nina-border-red   2.5s ease-in-out infinite; }
.nina-widget--warnings { animation: nina-border-amber  3s  ease-in-out infinite; }

@keyframes nina-spin { to { transform: rotate(360deg); } }
.nina-spinner {
  display: inline-block;
  font-size: 2rem;
  animation: nina-spin 1.2s linear infinite;
  align-self: center;
}

.nina-icon  { font-size: 1.5rem; align-self: center; }
.nina-error { color: #fca5a5; font-size: 0.85rem; text-align: center; }
.nina-ok    { font-size: 0.9rem; text-align: center; opacity: 0.75; }

.nina-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.75rem;
  opacity: 0.7;
}

.nina-dots { display: flex; gap: 4px; }
.nina-dot  { width: 6px; height: 6px; border-radius: 50%; background: #555; transition: background 0.2s; }
.nina-dot--active { background: #eee; }

.nina-card    { display: flex; flex-direction: column; gap: 4px; }
.nina-badge   {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 0.65rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.05em;
  align-self: flex-start;
}
.nina-headline {
  font-size: 0.85rem;
  font-weight: 600;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.35;
}
.nina-meta { font-size: 0.75rem; opacity: 0.6; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nina-time { font-size: 0.7rem; opacity: 0.5; }

/* ── 1×1 kompakt ── */
.nina-widget--compact { padding: 8px; gap: 4px; }

.nina-card--compact   { display: flex; flex-direction: column; gap: 3px; }

.nina-badge--compact  { font-size: 0.55rem; padding: 1px 5px; }

.nina-headline--compact {
  font-size: 0.7rem;
  font-weight: 600;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.25;
}

.nina-dots--compact { display: flex; gap: 3px; margin-top: 2px; }

/* ── 2×1 breit ── */
.nina-card--wide {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.nina-wide-body        { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }

.nina-headline--wide {
  font-size: 0.82rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Fade ── */
.nina-fade-enter-active,
.nina-fade-leave-active  { transition: opacity 0.35s ease; }
.nina-fade-enter-from,
.nina-fade-leave-to      { opacity: 0; }
</style>
