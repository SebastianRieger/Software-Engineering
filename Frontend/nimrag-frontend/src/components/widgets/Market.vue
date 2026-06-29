<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'
import type { Ref } from 'vue'
import type { CellSize } from '../../composables/useWidgetResize.ts'
import { loadAppConfig } from '../../composables/useAppConfig.ts'
import { getMarket } from '../../services/market.ts'
import type { AppConfig } from '../../types/appConfig.ts'
import type { MarketItem } from '../../types/market.ts'

const cellId    = inject<number>('cellId', 0)
const cellSizes = inject<Ref<Record<number, CellSize>>>('cellSizes', ref({}))

const size = computed(() => {
  switch (cellSizes.value[cellId]) {
    case 4:  return 'large'
    case 2:  return 'medium'
    default: return 'small'
  }
})

const items     = ref<MarketItem[]>([])
const isLoading = ref(true)
const error     = ref<string | null>(null)
let intervalId: ReturnType<typeof setInterval> | null = null

const visibleItems = computed(() => {
  if (size.value === 'large') return items.value
  return items.value.slice(0, size.value === 'medium' ? 4 : 2)
})

function trendClass(change: number): string {
  if (change > 0) return 'mkt-up'
  if (change < 0) return 'mkt-down'
  return 'mkt-flat'
}

function formatPrice(price: number, currency: string, assetType: 'stock' | 'crypto'): string {
  const fractionDigits = assetType === 'crypto' && price < 1 ? 4 : 2
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(price)
}

function formatChange(percentChange: number): string {
  const sign = percentChange >= 0 ? '+' : ''
  return `${sign}${percentChange.toFixed(2)}%`
}

async function load(appConfig?: AppConfig) {
  try {
    isLoading.value = true
    error.value = null
    const resolvedConfig = appConfig ?? await loadAppConfig()
    const marketConfig = resolvedConfig.widgets.market
    const response = await getMarket(marketConfig.symbols)
    const symbolOrder = new Map(marketConfig.symbols.map((s, i) => [s, i]))
    items.value = response.items
      .slice()
      .sort((a, b) => (symbolOrder.get(a.symbol) ?? 999) - (symbolOrder.get(b.symbol) ?? 999))
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
    }, appConfig.widgets.market.refresh_seconds * 1000)
  })
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})
</script>

<template>
  <div class="mkt-widget" :class="`mkt-widget--${size}`">

    <!-- Header -->
    <header class="mkt-header">
      <span class="mkt-logo">Market</span>
      <span v-if="isLoading" class="mkt-status mkt-status--loading"><span class="mkt-dot" /></span>
      <span v-else-if="error" class="mkt-status mkt-status--error" :title="error">!</span>
      <span v-else class="mkt-status mkt-status--updated">
        <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
        {{ new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }) }}
      </span>
    </header>

    <!-- Systemzustände -->
    <div v-if="error" class="mkt-empty">Kurse nicht verfügbar</div>
    <div v-else-if="isLoading" class="mkt-empty">Lädt…</div>
    <div v-else-if="!visibleItems.length" class="mkt-empty">Keine Kurse</div>

    <!-- SMALL: 2 Einträge, kompakte Liste -->
    <ul v-else-if="size === 'small'" class="mkt-list">
      <li
        v-for="item in visibleItems"
        :key="item.id"
        class="mkt-item"
        :class="trendClass(item.change)"
      >
        <span class="mkt-symbol">{{ item.symbol }}</span>
        <span class="mkt-price">{{ formatPrice(item.price, item.currency, item.asset_type) }}</span>
        <span class="mkt-pct" :class="trendClass(item.change)">{{ formatChange(item.percent_change) }}</span>
      </li>
    </ul>

    <!-- MEDIUM: 4 horizontale Zeilen mit Badge -->
    <div v-else-if="size === 'medium'" class="mkt-rows">
      <div
        v-for="item in visibleItems"
        :key="item.id"
        class="mkt-row"
        :class="trendClass(item.change)"
      >
        <span class="mkt-badge" :class="`mkt-badge--${item.asset_type}`">
          {{ item.asset_type === 'crypto' ? 'CRYPTO' : 'STOCK' }}
        </span>
        <div class="mkt-row-text">
          <p class="mkt-row-name">{{ item.name }}</p>
        </div>
        <div class="mkt-row-nums">
          <span class="mkt-price">{{ formatPrice(item.price, item.currency, item.asset_type) }}</span>
          <span class="mkt-pct" :class="trendClass(item.change)">{{ formatChange(item.percent_change) }}</span>
        </div>
      </div>
    </div>

    <!-- LARGE: alle Einträge, volle Details -->
    <div v-else-if="size === 'large'" class="mkt-large-list">
      <div
        v-for="item in visibleItems"
        :key="item.id"
        class="mkt-large-row"
        :class="trendClass(item.change)"
      >
        <div class="mkt-large-left">
          <span class="mkt-badge" :class="`mkt-badge--${item.asset_type}`">
            {{ item.asset_type === 'crypto' ? 'CRYPTO' : 'STOCK' }}
          </span>
          <div class="mkt-large-info">
            <span class="mkt-symbol">{{ item.symbol }}</span>
            <span class="mkt-name">{{ item.name }}</span>
          </div>
        </div>
        <div class="mkt-large-right">
          <span class="mkt-price">{{ formatPrice(item.price, item.currency, item.asset_type) }}</span>
          <span class="mkt-pct" :class="trendClass(item.change)">{{ formatChange(item.percent_change) }}</span>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* ── Variablen & Container ─────────────────────────── */
.mkt-widget {
  --c-bg:      #111;
  --c-surface: #1a1a1a;
  --c-border:  rgba(255,255,255,0.07);
  --c-text:    #e8e8e8;
  --c-muted:   #666;
  --c-up:      #27ae60;
  --c-down:    #c0392b;
  --font-ui:   'DM Mono', 'Courier New', monospace;
  --font-head: 'Georgia', 'Times New Roman', serif;

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
.mkt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.mkt-logo {
  font-family: var(--font-ui);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #fff;
  opacity: 0.9;
}

.mkt-status {
  font-family: var(--font-ui);
  font-size: 10px;
  color: var(--c-muted);
}

.mkt-status--error { color: var(--c-down); font-weight: 700; }

.mkt-status--updated {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.mkt-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  background: var(--c-muted);
  border-radius: 50%;
  animation: mkt-pulse 1.4s ease-in-out infinite;
}

@keyframes mkt-pulse {
  0%, 100% { opacity: 0.3; }
  50%       { opacity: 1; }
}

/* ── Leer / Fehler ─────────────────────────────────── */
.mkt-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--c-muted);
  letter-spacing: 0.08em;
}

/* ── Trend-Farben ──────────────────────────────────── */
.mkt-up   { color: var(--c-up); }
.mkt-down { color: var(--c-down); }
.mkt-flat { color: var(--c-muted); }

/* ── SMALL: kompakte 2-Zeilen-Liste ───────────────── */
.mkt-list {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.mkt-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px;
  border-bottom: 1px solid var(--c-border);
  overflow: hidden;
  color: var(--c-text);
}

.mkt-item:last-child { border-bottom: none; }

.mkt-symbol {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--c-text);
  flex-shrink: 0;
  min-width: 64px;
}

.mkt-price {
  font-size: 11px;
  color: var(--c-text);
  flex: 1;
  text-align: right;
  white-space: nowrap;
}

.mkt-pct {
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
  min-width: 52px;
  text-align: right;
  white-space: nowrap;
}

/* ── MEDIUM: horizontale Zeilen ───────────────────── */
.mkt-rows {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.mkt-row {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--c-border);
  overflow: hidden;
  min-height: 0;
  color: var(--c-text);
}

.mkt-row:last-child { border-bottom: none; }

.mkt-badge {
  font-size: 8px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--c-muted);
  border: 1px solid var(--c-border);
  padding: 2px 5px;
  border-radius: 2px;
  flex-shrink: 0;
  white-space: nowrap;
}

.mkt-badge--crypto { border-color: rgba(39,174,96,0.4); color: rgba(39,174,96,0.85); }
.mkt-badge--stock  { border-color: rgba(255,255,255,0.12); color: var(--c-muted); }

.mkt-row-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.mkt-row-name {
  margin: 0;
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--c-text);
}

.mkt-row-nums {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
  flex-shrink: 0;
}

.mkt-widget--medium .mkt-price {
  font-size: 11px;
  color: var(--c-text);
  white-space: nowrap;
}

.mkt-widget--medium .mkt-pct {
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}

/* ── LARGE: volle Detailliste ─────────────────────── */
.mkt-large-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 4px 0;
}

.mkt-large-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
  color: var(--c-text);
}

.mkt-large-row:last-child { border-bottom: none; }

.mkt-large-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.mkt-large-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.mkt-large-info .mkt-symbol {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--c-text);
}

.mkt-name {
  font-size: 10px;
  color: var(--c-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mkt-large-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
  flex-shrink: 0;
}

.mkt-large-right .mkt-price {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-text);
  white-space: nowrap;
}

.mkt-large-right .mkt-pct {
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}
</style>
