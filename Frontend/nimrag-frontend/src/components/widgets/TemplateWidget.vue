<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { apiClient, ApiError } from '../../services/api'
import { realtimeClient } from '../../services/realtime'
import type { HardwareStatusWidgetSettings } from '../../types/config'
import type {
  GestureStatusResponse,
  LEDStateResponse,
  RealtimeEvent,
  SystemStatusResponse,
  VoiceStatusResponse,
} from '../../types/hardware'

const props = defineProps<{
  widgetId?: string
  settings?: HardwareStatusWidgetSettings
  updateSettings?: (nextSettingsPatch: Partial<HardwareStatusWidgetSettings>) => void
}>()

const systemStatus = ref<SystemStatusResponse | null>(null)
const gestureStatus = ref<GestureStatusResponse | null>(null)
const ledStatus = ref<LEDStateResponse | null>(null)
const voiceStatus = ref<VoiceStatusResponse | null>(null)
const gesturePreview = ref<string | null>(null)
const lastRealtimeEvent = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
let refreshTimer: number | null = null
let unsubscribeRealtime: (() => void) | null = null

const effectiveSettings = computed<Required<HardwareStatusWidgetSettings>>(() => ({
  showPreview: props.settings?.showPreview ?? false,
  autoRefresh: props.settings?.autoRefresh ?? true,
}))

const isPreviewMode = computed(() => !props.widgetId)

function formatErrorMessage(value: unknown): string {
  if (value instanceof ApiError) {
    return value.message
  }
  if (value instanceof Error) {
    return value.message
  }
  return 'Hardwarestatus konnte nicht geladen werden.'
}

async function loadStatuses(): Promise<void> {
  if (isPreviewMode.value) {
    return
  }

  loading.value = true
  error.value = null

  try {
    const [system, gesture, led, voice] = await Promise.all([
      apiClient.getSystemStatus(),
      apiClient.getGestureStatus(),
      apiClient.getLedStatus(),
      apiClient.getVoiceStatus(),
    ])

    systemStatus.value = system
    gestureStatus.value = gesture
    ledStatus.value = led
    voiceStatus.value = voice

    if (effectiveSettings.value.showPreview) {
      await loadPreviewFrame()
    }
  } catch (loadError) {
    error.value = formatErrorMessage(loadError)
  } finally {
    loading.value = false
  }
}

async function loadPreviewFrame(): Promise<void> {
  try {
    const response = await apiClient.getGestureFrame()
    gesturePreview.value = `data:image/jpeg;base64,${response.image}`
  } catch {
    gesturePreview.value = null
  }
}

function scheduleRefresh(): void {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }

  if (!effectiveSettings.value.autoRefresh || isPreviewMode.value) {
    return
  }

  refreshTimer = window.setInterval(() => {
    void loadStatuses()
  }, 5000)
}

function updateSettings(nextSettingsPatch: Partial<HardwareStatusWidgetSettings>): void {
  props.updateSettings?.(nextSettingsPatch)
}

async function startGestures(): Promise<void> {
  try {
    gestureStatus.value = await apiClient.startGestures(0)
    if (effectiveSettings.value.showPreview) {
      await loadPreviewFrame()
    }
  } catch (startError) {
    error.value = formatErrorMessage(startError)
  }
}

async function stopGestures(): Promise<void> {
  try {
    gestureStatus.value = await apiClient.stopGestures()
  } catch (stopError) {
    error.value = formatErrorMessage(stopError)
  }
}

async function applyLedPreset(color: { red: number; green: number; blue: number }): Promise<void> {
  try {
    ledStatus.value = await apiClient.setLedColor(color)
  } catch (ledError) {
    error.value = formatErrorMessage(ledError)
  }
}

async function changeBrightness(event: Event): Promise<void> {
  const target = event.target as HTMLInputElement
  const brightness = Number(target.value)
  if (Number.isNaN(brightness)) {
    return
  }

  try {
    ledStatus.value = await apiClient.setLedBrightness(brightness)
  } catch (ledError) {
    error.value = formatErrorMessage(ledError)
  }
}

function handleRealtimeEvent(event: RealtimeEvent): void {
  lastRealtimeEvent.value = event.eventType

  if (event.eventType === 'GestureDetected') {
    void loadStatuses()
    if (effectiveSettings.value.showPreview) {
      void loadPreviewFrame()
    }
    return
  }

  if (event.eventType === 'LEDStateChanged') {
    ledStatus.value = event.payload as unknown as LEDStateResponse
  }
}

onMounted(() => {
  if (isPreviewMode.value) {
    return
  }

  scheduleRefresh()
  void loadStatuses()
  unsubscribeRealtime = realtimeClient.subscribe(handleRealtimeEvent)
})

watch(
  () => effectiveSettings.value,
  (nextSettings, previousSettings) => {
    if (isPreviewMode.value) {
      return
    }

    scheduleRefresh()

    if (!nextSettings.showPreview) {
      gesturePreview.value = null
      return
    }

    if (!previousSettings || nextSettings.showPreview !== previousSettings.showPreview) {
      void loadPreviewFrame()
    }
  },
  { deep: true },
)

onBeforeUnmount(() => {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
  }
  unsubscribeRealtime?.()
})
</script>

<template>
  <div class="card">
    <template v-if="isPreviewMode">
      <h3>Hardware</h3>
      <p class="preview-copy">Status fuer Kamera, LED und Voice.</p>
    </template>

    <template v-else>
      <div class="header-row">
        <h3>Hardware</h3>
        <button class="secondary-btn" @click="loadStatuses">Aktualisieren</button>
      </div>

      <p v-if="loading" class="meta-text">Status wird geladen...</p>
      <p v-else-if="error" class="error-text">{{ error }}</p>

      <div class="status-grid">
        <div class="status-tile">
          <span class="status-label">System</span>
          <strong>{{ systemStatus?.status ?? '--' }}</strong>
          <span class="meta-text">Config {{ systemStatus?.config_entries ?? 0 }} · Cache {{ systemStatus?.weather_cache_entries ?? 0 }}</span>
        </div>

        <div class="status-tile">
          <span class="status-label">Gesten</span>
          <strong>{{ gestureStatus?.running ? 'aktiv' : 'inaktiv' }}</strong>
          <span class="meta-text">{{ gestureStatus?.available ? 'Kamera bereit' : 'Kamera nicht verfuegbar' }}</span>
          <span class="meta-text">Letzte Geste: {{ gestureStatus?.last_gesture ?? 'keine' }}</span>
        </div>

        <div class="status-tile">
          <span class="status-label">LED</span>
          <strong>{{ ledStatus?.mode ?? '--' }}</strong>
          <span class="meta-text">Helligkeit {{ ledStatus ? Math.round(ledStatus.brightness * 100) : 0 }}%</span>
          <span class="meta-text">{{ ledStatus?.available ? 'Hardware aktiv' : 'Mock/Fallback' }}</span>
        </div>

        <div class="status-tile">
          <span class="status-label">Voice</span>
          <strong>{{ voiceStatus?.mode ?? '--' }}</strong>
          <span class="meta-text">{{ voiceStatus?.available ? 'bereit' : 'noch nicht verdrahtet' }}</span>
          <span class="meta-text">{{ voiceStatus?.last_error ?? 'kein Sprachereignis' }}</span>
        </div>
      </div>

      <div class="control-block">
        <div class="control-row">
          <button class="action-btn" @click="startGestures">Gesten starten</button>
          <button class="action-btn" @click="stopGestures">Gesten stoppen</button>
          <button class="secondary-btn" @click="updateSettings({ autoRefresh: !effectiveSettings.autoRefresh })">
            {{ effectiveSettings.autoRefresh ? 'Auto-Refresh an' : 'Auto-Refresh aus' }}
          </button>
          <button class="secondary-btn" @click="updateSettings({ showPreview: !effectiveSettings.showPreview })">
            {{ effectiveSettings.showPreview ? 'Preview an' : 'Preview aus' }}
          </button>
        </div>

        <div class="control-row">
          <button class="preset-btn warm" @click="applyLedPreset({ red: 1, green: 0.45, blue: 0.1 })">Warm</button>
          <button class="preset-btn cool" @click="applyLedPreset({ red: 0.15, green: 0.45, blue: 1 })">Kalt</button>
          <button class="preset-btn neutral" @click="applyLedPreset({ red: 0.8, green: 0.8, blue: 0.8 })">Neutral</button>
          <label class="slider-group">
            <span>LED</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              :value="ledStatus?.brightness ?? 1"
              @input="changeBrightness"
            >
          </label>
        </div>
      </div>

      <div v-if="effectiveSettings.showPreview" class="preview-block">
        <img v-if="gesturePreview" :src="gesturePreview" alt="Gesture preview" class="preview-image">
        <p v-else class="meta-text">Kein Preview-Frame verfuegbar.</p>
      </div>

      <p class="footer-note">Realtime: {{ lastRealtimeEvent ?? 'noch kein Ereignis' }}</p>
    </template>
  </div>
</template>

<style scoped>
.card {
  width: 100%;
  height: 100%;
  background: linear-gradient(160deg, #16110c 0%, #0d1720 100%);
  color: #f8fafc;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row,
.control-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.status-tile {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
}

.status-label,
.meta-text,
.footer-note,
.preview-copy {
  font-size: 0.8rem;
  opacity: 0.75;
}

.action-btn,
.secondary-btn,
.preset-btn {
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 999px;
  color: inherit;
  background: rgba(255, 255, 255, 0.08);
  padding: 6px 10px;
  cursor: pointer;
}

.preset-btn.warm { background: rgba(249, 115, 22, 0.18); }
.preset-btn.cool { background: rgba(59, 130, 246, 0.18); }
.preset-btn.neutral { background: rgba(148, 163, 184, 0.18); }

.slider-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.preview-block {
  flex: 1;
  min-height: 0;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.04);
  display: grid;
  place-items: center;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.error-text {
  color: #fca5a5;
}

@media (max-width: 700px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>