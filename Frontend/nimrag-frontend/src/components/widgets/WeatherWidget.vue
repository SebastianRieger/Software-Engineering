<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { ApiError } from '../../services/api'
import { getCurrentWeather } from '../../services/weather'
import type { WeatherCurrentResponse } from '../../types/weather'

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

async function loadWeather(): Promise<void> {
  loading.value = true
  error.value = null

  try {
    weatherData.value = await getCurrentWeather()
  } catch (loadError) {
    weatherData.value = null
    error.value = formatErrorMessage(loadError)
  } finally {
    loading.value = false
  }
}

const locationLabel = computed(() => weatherData.value?.location_name ?? 'Unbekannter Ort')
const temperatureLabel = computed(() => {
  if (!weatherData.value) {
    return '--'
  }

  return `${Math.round(weatherData.value.temperature)}°C`
})

onMounted(() => {
  refreshTimer = window.setInterval(() => {
    void loadWeather()
  }, 15 * 60 * 1000)
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
      <p>{{ locationLabel }} · {{ weatherData.condition }} · {{ temperatureLabel }}</p>
      <p class="meta">
        Luftfeuchte {{ weatherData.humidity }}% · Wind {{ weatherData.wind_speed.toFixed(1) }} m/s
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
