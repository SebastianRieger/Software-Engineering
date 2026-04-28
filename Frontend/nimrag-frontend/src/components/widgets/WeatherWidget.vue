<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { apiClient, ApiError } from '../../services/api'
import type { SystemConfig } from '../../types/config'
import type { WeatherCurrentResponse } from '../../types/weather'

const props = defineProps<{
  initialSystemConfig?: SystemConfig | null
}>()

const systemConfig = ref<SystemConfig | null>(props.initialSystemConfig ?? null)
const weatherData = ref<WeatherCurrentResponse | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
let refreshTimer: number | null = null

function clearRefreshTimer(): void {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }
}

function formatErrorMessage(value: unknown): string {
  if (value instanceof ApiError) {
    return value.message
  }
  if (value instanceof Error) {
    return value.message
  }
  return 'Wetterdaten sind derzeit nicht verfuegbar.'
}

function scheduleRefresh(): void {
  clearRefreshTimer()
  if (!systemConfig.value) {
    return
  }

  refreshTimer = window.setInterval(() => {
    void loadWeather()
  }, systemConfig.value.weather_refresh_seconds * 1000)
}

async function ensureSystemConfig(): Promise<SystemConfig> {
  if (systemConfig.value) {
    return systemConfig.value
  }

  const response = await apiClient.getSystemConfig()
  systemConfig.value = response.config
  scheduleRefresh()
  return response.config
}

async function loadWeather(): Promise<void> {
  loading.value = true
  error.value = null

  try {
    const currentSystemConfig = await ensureSystemConfig()
    weatherData.value = await apiClient.getCurrentWeather({
      lat: currentSystemConfig.latitude,
      lon: currentSystemConfig.longitude,
    })
  } catch (loadError) {
    weatherData.value = null
    error.value = formatErrorMessage(loadError)
  } finally {
    loading.value = false
  }
}

const displayLocation = computed(() => {
  return weatherData.value?.location_name ?? systemConfig.value?.location_name ?? 'Unbekannter Ort'
})

const temperatureLabel = computed(() => {
  if (!weatherData.value) {
    return '--'
  }

  const suffix = systemConfig.value?.units === 'imperial' ? 'F' : 'C'
  return `${Math.round(weatherData.value.temperature)}°${suffix}`
})

watch(
  () => props.initialSystemConfig,
  (nextConfig) => {
    if (!nextConfig) {
      return
    }
    systemConfig.value = nextConfig
    scheduleRefresh()
    void loadWeather()
  },
)

onMounted(() => {
  scheduleRefresh()
  void loadWeather()
})

onBeforeUnmount(() => {
  clearRefreshTimer()
})
</script>

<template>
  <div class="w-full h-full card flex flex-col justify-center">
    <h3>Wetter</h3>
    <p v-if="loading">Lade Wetterdaten...</p>
    <template v-else-if="weatherData">
      <p>{{ displayLocation }} · {{ weatherData.condition }} · {{ temperatureLabel }}</p>
      <p class="meta">
        Luftfeuchte {{ weatherData.humidity }}% · Wind {{ weatherData.wind_speed.toFixed(1) }} m/s · {{ weatherData.source }}
      </p>
    </template>
    <p v-else class="error">{{ error }}</p>
  </div>
</template>

<style scoped>
.card { background:#111; color:#eee; padding:16px; }
.meta { margin-top: 8px; font-size: 0.9rem; opacity: 0.75; }
.error { color: #fca5a5; }
</style>
