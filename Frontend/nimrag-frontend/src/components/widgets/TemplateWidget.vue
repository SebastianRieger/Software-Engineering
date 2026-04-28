<script setup lang="ts">
import type { HardwareStatusWidgetSettings } from '../../types/config'
import { LED_PRESETS, useHardwareWidget } from '../../utils/hardwareWidget'

const props = defineProps<{
  widgetId?: string
  settings?: HardwareStatusWidgetSettings
  updateSettings?: (nextSettingsPatch: Partial<HardwareStatusWidgetSettings>) => void
}>()

const {
  applyLedPreset,
  changeBrightness,
  effectiveSettings,
  error,
  gestureDevices,
  gesturePreview,
  gestureStatus,
  isPreviewMode,
  lastRealtimeEvent,
  ledStatus,
  loadStatuses,
  loading,
  selectGestureCamera,
  selectVoiceDevice,
  startGestures,
  startVoice,
  stopGestures,
  stopVoice,
  systemStatus,
  updateSettings,
  voiceDevices,
  voiceStatus,
} = useHardwareWidget(props)
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
          <span class="meta-text">{{ gestureStatus?.camera_name ?? 'kein Kamerageraet gewaehlt' }}</span>
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
          <span class="meta-text">{{ voiceStatus?.available ? 'bereit' : 'nicht verfuegbar' }}</span>
          <span class="meta-text">{{ voiceStatus?.device_name ?? 'kein Mikrofon gewaehlt' }}</span>
          <span class="meta-text">{{ voiceStatus?.last_error ?? 'kein Sprachereignis' }}</span>
        </div>
      </div>

      <div class="control-block">
        <div class="control-row">
          <label class="device-select-group">
            <span>Kamera</span>
            <select class="device-select" :value="effectiveSettings.gestureCameraIndex" @change="selectGestureCamera">
              <option v-if="gestureDevices.length === 0" :value="effectiveSettings.gestureCameraIndex">Keine Kamera gefunden</option>
              <option v-for="device in gestureDevices" :key="device.index" :value="device.index">
                {{ device.name }} · #{{ device.index }}
              </option>
            </select>
          </label>
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
          <label class="device-select-group">
            <span>Mikrofon</span>
            <select class="device-select" :value="effectiveSettings.voiceDeviceIndex" @change="selectVoiceDevice">
              <option value="-1">Systemstandard</option>
              <option v-if="voiceDevices.length === 0" :value="effectiveSettings.voiceDeviceIndex">Keine Eingabegeraete gefunden</option>
              <option v-for="device in voiceDevices" :key="device.index" :value="device.index">
                {{ device.name }} · #{{ device.index }}
              </option>
            </select>
          </label>
          <button class="action-btn" @click="startVoice">Voice starten</button>
          <button class="action-btn" @click="stopVoice">Voice stoppen</button>
          <button
            v-for="preset in LED_PRESETS"
            :key="preset.label"
            class="preset-btn"
            :class="preset.tone"
            @click="applyLedPreset(preset.color)"
          >
            {{ preset.label }}
          </button>
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

.device-select-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.device-select {
  min-width: 190px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: inherit;
  padding: 6px 10px;
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