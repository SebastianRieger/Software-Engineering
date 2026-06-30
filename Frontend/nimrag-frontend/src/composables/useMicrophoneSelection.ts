import { ref } from 'vue'
import { buildApiUrl } from '../services/apiConfig'
import { warnDevOnce } from '../utils/devWarnings'

export interface MicDevice {
  index: number
  name: string
  max_input_channels: number
  default_samplerate: number
  is_default: boolean
}

export interface VoiceStatus {
  message: string
  available: boolean
  enabled: boolean
  running: boolean
  device_index: number | null
  device_name: string | null
  last_error: string | null
}

export interface MicrophoneSelectionResult {
  ok: boolean
  message: string | null
  status: VoiceStatus | null
}

function toErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message
  }

  return fallback
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string; message?: string }
    if (typeof data.detail === 'string' && data.detail.trim().length > 0) {
      return data.detail
    }
    if (typeof data.message === 'string' && data.message.trim().length > 0) {
      return data.message
    }
  } catch {
    // fall back to the provided message below
  }

  return fallback
}

export function useMicrophoneSelection() {
  const devices = ref<MicDevice[]>([])
  const activeDeviceIndex = ref<number | null>(null)
  const deviceName = ref<string | null>(null)
  const isRunning = ref(false)
  const isAvailable = ref(true)
  const isEnabled = ref(true)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const lastBackendError = ref<string | null>(null)

  function applyStatus(status: VoiceStatus): void {
    isRunning.value = Boolean(status.running)
    isAvailable.value = Boolean(status.available)
    isEnabled.value = Boolean(status.enabled)
    activeDeviceIndex.value = status.device_index ?? null
    deviceName.value = status.device_name ?? null
    lastBackendError.value = status.last_error ?? null
  }

  async function fetchDevices(): Promise<void> {
    try {
      const res = await fetch(buildApiUrl('voice/devices'))
      if (!res.ok) {
        throw new Error(await readErrorMessage(res, 'Mikrofone konnten nicht geladen werden.'))
      }

      const data = (await res.json()) as { devices: MicDevice[] }
      devices.value = data.devices ?? []
    } catch (err) {
      devices.value = []
      const message = toErrorMessage(err, 'Mikrofone konnten nicht geladen werden.')
      error.value = message
      warnDevOnce('voice', message, err)
    }
  }

  async function fetchStatus(): Promise<VoiceStatus | null> {
    try {
      const res = await fetch(buildApiUrl('voice/status'))
      if (!res.ok) {
        throw new Error(await readErrorMessage(res, 'Sprachstatus konnte nicht geladen werden.'))
      }

      const data = (await res.json()) as VoiceStatus
      applyStatus(data)
      error.value = null
      return data
    } catch (err) {
      const message = toErrorMessage(err, 'Sprachstatus konnte nicht geladen werden.')
      isRunning.value = false
      lastBackendError.value = message
      warnDevOnce('voice', message, err)
      return null
    }
  }

  async function selectDevice(deviceIndex: number): Promise<MicrophoneSelectionResult> {
    isLoading.value = true
    error.value = null

    let status: VoiceStatus | null = null
    try {
      const stopRes = await fetch(buildApiUrl('voice/stop'), { method: 'POST' })
      if (!stopRes.ok) {
        throw new Error(await readErrorMessage(stopRes, 'Mikrofon konnte nicht gestoppt werden.'))
      }

      const startRes = await fetch(buildApiUrl('voice/start'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_index: deviceIndex }),
      })

      if (!startRes.ok) {
        const message = await readErrorMessage(
          startRes,
          'Mikrofon konnte nicht gestartet werden.',
        )
        error.value = message
        status = await fetchStatus()
        return { ok: false, message: status?.last_error ?? message, status }
      }

      status = (await startRes.json()) as VoiceStatus
      applyStatus(status)

      const POLL_INTERVAL_MS = 250
      const MAX_POLLS = 12

      for (let poll = 0; poll < MAX_POLLS && !(status?.running ?? false); poll++) {
        await new Promise<void>((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
        status = await fetchStatus()
        if (status?.running) {
          break
        }
      }

      if (!status?.running) {
        const message = status?.last_error
          ?? 'Mikrofon konnte nicht gestartet werden. Bitte ein anderes Gerät wählen.'
        error.value = message
        return { ok: false, message, status }
      }

      error.value = null
      await fetchDevices()
      return { ok: true, message: null, status }
    } catch (err) {
      const message = toErrorMessage(err, 'Verbindungsfehler')
      error.value = message
      warnDevOnce('voice', message, err)
      return { ok: false, message, status }
    } finally {
      isLoading.value = false
    }
  }

  async function init(): Promise<void> {
    await Promise.all([fetchDevices(), fetchStatus()])
  }

  return {
    devices,
    activeDeviceIndex,
    deviceName,
    isRunning,
    isAvailable,
    isEnabled,
    isLoading,
    error,
    lastBackendError,
    selectDevice,
    init,
    fetchDevices,
    fetchStatus,
  }
}
