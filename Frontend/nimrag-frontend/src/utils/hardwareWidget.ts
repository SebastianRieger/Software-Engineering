import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { ApiError, apiClient } from '../services/api'
import { realtimeClient } from '../services/realtime'
import type { HardwareStatusWidgetSettings } from '../types/config'
import type {
  GestureStatusResponse,
  LEDColor,
  LEDStateResponse,
  RealtimeEvent,
  SystemStatusResponse,
  VoiceStatusResponse,
} from '../types/hardware'

interface HardwareWidgetProps {
  widgetId?: string
  settings?: HardwareStatusWidgetSettings
  updateSettings?: (nextSettingsPatch: Partial<HardwareStatusWidgetSettings>) => void
}

export const HARDWARE_WIDGET_DEFAULT_SETTINGS: Required<HardwareStatusWidgetSettings> = {
  showPreview: false,
  autoRefresh: true,
}

export const LED_PRESETS: Array<{ label: string; tone: 'warm' | 'cool' | 'neutral'; color: LEDColor }> = [
  { label: 'Warm', tone: 'warm', color: { red: 1, green: 0.45, blue: 0.1 } },
  { label: 'Kalt', tone: 'cool', color: { red: 0.15, green: 0.45, blue: 1 } },
  { label: 'Neutral', tone: 'neutral', color: { red: 0.8, green: 0.8, blue: 0.8 } },
]

export function formatHardwareError(value: unknown): string {
  if (value instanceof ApiError) {
    return value.message
  }
  if (value instanceof Error) {
    return value.message
  }
  return 'Hardwarestatus konnte nicht geladen werden.'
}

export function useHardwareWidget(props: HardwareWidgetProps) {
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
    showPreview: props.settings?.showPreview ?? HARDWARE_WIDGET_DEFAULT_SETTINGS.showPreview,
    autoRefresh: props.settings?.autoRefresh ?? HARDWARE_WIDGET_DEFAULT_SETTINGS.autoRefresh,
  }))

  const isPreviewMode = computed(() => !props.widgetId)

  async function loadPreviewFrame(): Promise<void> {
    try {
      const response = await apiClient.getGestureFrame()
      gesturePreview.value = `data:image/jpeg;base64,${response.image}`
    } catch {
      gesturePreview.value = null
    }
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
      error.value = formatHardwareError(loadError)
    } finally {
      loading.value = false
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
      error.value = formatHardwareError(startError)
    }
  }

  async function stopGestures(): Promise<void> {
    try {
      gestureStatus.value = await apiClient.stopGestures()
    } catch (stopError) {
      error.value = formatHardwareError(stopError)
    }
  }

  async function applyLedPreset(color: LEDColor): Promise<void> {
    try {
      ledStatus.value = await apiClient.setLedColor(color)
    } catch (ledError) {
      error.value = formatHardwareError(ledError)
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
      error.value = formatHardwareError(ledError)
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

  return {
    applyLedPreset,
    changeBrightness,
    effectiveSettings,
    error,
    gesturePreview,
    gestureStatus,
    isPreviewMode,
    lastRealtimeEvent,
    ledStatus,
    loadStatuses,
    loading,
    startGestures,
    stopGestures,
    systemStatus,
    updateSettings,
    voiceStatus,
  }
}