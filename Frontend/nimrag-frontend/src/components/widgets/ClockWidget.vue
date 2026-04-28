<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import type { ClockWidgetSettings } from '../../types/config'

const props = defineProps<{
  widgetId?: string
  settings?: ClockWidgetSettings
  updateSettings?: (nextSettingsPatch: Partial<ClockWidgetSettings>) => void
}>()

const now = ref(new Date())
let timer: number | null = null

const effectiveSettings = computed<Required<ClockWidgetSettings>>(() => ({
  format: props.settings?.format === '12h' ? '12h' : '24h',
  showSeconds: props.settings?.showSeconds ?? true,
  timezoneMode: props.settings?.timezoneMode === 'utc' ? 'utc' : 'browser',
}))

const timeLabel = computed(() => {
  const options: Intl.DateTimeFormatOptions = {
    hour: '2-digit',
    minute: '2-digit',
    second: effectiveSettings.value.showSeconds ? '2-digit' : undefined,
    hour12: effectiveSettings.value.format === '12h',
    timeZone: effectiveSettings.value.timezoneMode === 'utc' ? 'UTC' : undefined,
  }

  return new Intl.DateTimeFormat('de-DE', options).format(now.value)
})

const zoneLabel = computed(() => effectiveSettings.value.timezoneMode === 'utc' ? 'UTC' : 'Lokale Zeit')

function pushSettings(nextSettingsPatch: Partial<ClockWidgetSettings>): void {
  props.updateSettings?.(nextSettingsPatch)
}

onMounted(() => {
  timer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
})

onBeforeUnmount(() => {
  if (timer !== null) {
    window.clearInterval(timer)
  }
})
</script>

<template>
  <div class="card">
    <div class="header-row">
      <h3>Uhr</h3>
      <span class="zone-label">{{ zoneLabel }}</span>
    </div>
    <p class="time-label">{{ timeLabel }}</p>
    <div v-if="updateSettings" class="control-row">
      <button class="toggle-btn" @click="pushSettings({ format: effectiveSettings.format === '24h' ? '12h' : '24h' })">
        {{ effectiveSettings.format }}
      </button>
      <button class="toggle-btn" @click="pushSettings({ showSeconds: !effectiveSettings.showSeconds })">
        {{ effectiveSettings.showSeconds ? 'Sekunden an' : 'Sekunden aus' }}
      </button>
      <button class="toggle-btn" @click="pushSettings({ timezoneMode: effectiveSettings.timezoneMode === 'browser' ? 'utc' : 'browser' })">
        {{ effectiveSettings.timezoneMode === 'browser' ? 'UTC' : 'Browser' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.card {
  width: 100%;
  height: 100%;
  background: linear-gradient(160deg, #121826 0%, #0a0f19 100%);
  color: #eef2ff;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.zone-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.7;
}

.time-label {
  margin: 0;
  font-size: clamp(1.8rem, 5vw, 3rem);
  font-variant-numeric: tabular-nums;
}

.control-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.toggle-btn {
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.08);
  color: inherit;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 0.8rem;
  cursor: pointer;
}
</style>