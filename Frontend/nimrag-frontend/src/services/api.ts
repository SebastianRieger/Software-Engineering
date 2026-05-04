import { buildApiUrl } from './apiConfig'
import type {
  CalibrationApplyResponse,
  CalibrationDefinitionsResponse,
  CalibrationRollbackResponse,
  CalibrationSessionCreateRequest,
  CalibrationSessionResponse,
} from '../types/calibration'
import type { LayoutConfig, LayoutConfigEnvelope, SystemConfig, SystemConfigEnvelope } from '../types/config'
import type {
  CommandProfilesConfig,
  CommandProfilesConfigEnvelope,
  MusicalAudioConfig,
  MusicalAudioConfigEnvelope,
  MusicalAudioTrainingArtifact,
  MusicalAudioTrainingArtifactEnvelope,
  MusicalAudioTrainingArtifactListEnvelope,
} from '../types/commands'
import type {
  GestureCameraListResponse,
  GestureFrameResponse,
  GestureStatusResponse,
  LEDStateResponse,
  MusicalAudioInputDeviceListResponse,
  MusicalAudioStatusResponse,
  SystemStatusResponse,
  VoiceInputDeviceListResponse,
  VoiceStatusResponse,
} from '../types/hardware'
import type { InputActionConfig, InputActionConfigEnvelope } from '../types/interactions'
import type { WeatherCurrentResponse } from '../types/weather'

type QueryValue = string | number | boolean | null | undefined

const REQUEST_RETRY_COUNT = 3
const REQUEST_RETRY_DELAY_MS = 400

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function buildQuery(params: Record<string, QueryValue>): string {
  const searchParams = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return
    }
    searchParams.set(key, String(value))
  })

  const query = searchParams.toString()
  return query ? `?${query}` : ''
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

function isRetryableNetworkError(error: unknown): boolean {
  return error instanceof TypeError
}

function isRetryableStatus(status: number): boolean {
  return status === 502 || status === 503 || status === 504
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let attempt = 0

  while (true) {
    try {
      const response = await fetch(buildApiUrl(path), {
        ...init,
        headers: {
          Accept: 'application/json',
          ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
          ...(init?.headers ?? {}),
        },
      })

      const responseText = await response.text()
      const responseData = responseText ? JSON.parse(responseText) : null

      if (!response.ok) {
        if (attempt < REQUEST_RETRY_COUNT && isRetryableStatus(response.status)) {
          attempt += 1
          await sleep(REQUEST_RETRY_DELAY_MS * attempt)
          continue
        }

        const message = typeof responseData?.detail === 'string'
          ? responseData.detail
          : `Request failed with status ${response.status}`
        throw new ApiError(message, response.status)
      }

      return responseData as T
    } catch (error) {
      if (attempt < REQUEST_RETRY_COUNT && isRetryableNetworkError(error)) {
        attempt += 1
        await sleep(REQUEST_RETRY_DELAY_MS * attempt)
        continue
      }
      throw error
    }
  }
}

export const apiClient = {
  getLayout(profile = 'default'): Promise<LayoutConfigEnvelope> {
    return requestJson<LayoutConfigEnvelope>(`/config/layout${buildQuery({ profile })}`)
  },

  saveLayout(layout: LayoutConfig, profile = 'default'): Promise<LayoutConfigEnvelope> {
    return requestJson<LayoutConfigEnvelope>(`/config/layout${buildQuery({ profile })}`, {
      method: 'PUT',
      body: JSON.stringify(layout),
    })
  },

  getSystemConfig(): Promise<SystemConfigEnvelope> {
    return requestJson<SystemConfigEnvelope>('/config/system')
  },

  saveSystemConfig(config: SystemConfig): Promise<SystemConfigEnvelope> {
    return requestJson<SystemConfigEnvelope>('/config/system', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  },

  getInputActionConfig(): Promise<InputActionConfigEnvelope> {
    return requestJson<InputActionConfigEnvelope>('/config/input-actions')
  },

  saveInputActionConfig(config: InputActionConfig): Promise<InputActionConfigEnvelope> {
    return requestJson<InputActionConfigEnvelope>('/config/input-actions', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  },

  getCommandProfilesConfig(): Promise<CommandProfilesConfigEnvelope> {
    return requestJson<CommandProfilesConfigEnvelope>('/config/command-profiles')
  },

  saveCommandProfilesConfig(config: CommandProfilesConfig): Promise<CommandProfilesConfigEnvelope> {
    return requestJson<CommandProfilesConfigEnvelope>('/config/command-profiles', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  },

  getMusicalAudioConfig(): Promise<MusicalAudioConfigEnvelope> {
    return requestJson<MusicalAudioConfigEnvelope>('/config/musical-audio')
  },

  saveMusicalAudioConfig(config: MusicalAudioConfig): Promise<MusicalAudioConfigEnvelope> {
    return requestJson<MusicalAudioConfigEnvelope>('/config/musical-audio', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  },

  listMusicalAudioArtifacts(profile = 'default'): Promise<MusicalAudioTrainingArtifactListEnvelope> {
    return requestJson<MusicalAudioTrainingArtifactListEnvelope>(`/config/musical-audio/artifacts${buildQuery({ profile })}`)
  },

  getMusicalAudioArtifact(artifactId: string, profile = 'default'): Promise<MusicalAudioTrainingArtifactEnvelope> {
    return requestJson<MusicalAudioTrainingArtifactEnvelope>(`/config/musical-audio/artifacts/${artifactId}${buildQuery({ profile })}`)
  },

  saveMusicalAudioArtifact(artifact: MusicalAudioTrainingArtifact): Promise<MusicalAudioTrainingArtifactEnvelope> {
    return requestJson<MusicalAudioTrainingArtifactEnvelope>(`/config/musical-audio/artifacts/${artifact.artifact_id}`, {
      method: 'PUT',
      body: JSON.stringify(artifact),
    })
  },

  deleteMusicalAudioArtifact(artifactId: string, profile = 'default'): Promise<{ deleted: boolean; artifact_id: string; profile: string }> {
    return requestJson<{ deleted: boolean; artifact_id: string; profile: string }>(`/config/musical-audio/artifacts/${artifactId}${buildQuery({ profile })}`, {
      method: 'DELETE',
    })
  },

  getCurrentWeather(params?: { lat?: number; lon?: number }): Promise<WeatherCurrentResponse> {
    return requestJson<WeatherCurrentResponse>(`/weather/current${buildQuery(params ?? {})}`)
  },

  getSystemStatus(): Promise<SystemStatusResponse> {
    return requestJson<SystemStatusResponse>('/system/status')
  },

  getCalibrationDefinitions(): Promise<CalibrationDefinitionsResponse> {
    return requestJson<CalibrationDefinitionsResponse>('/calibration/definitions')
  },

  startCalibrationSession(payload: CalibrationSessionCreateRequest): Promise<CalibrationSessionResponse> {
    return requestJson<CalibrationSessionResponse>('/calibration/sessions', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  getCalibrationSession(sessionId: string): Promise<CalibrationSessionResponse> {
    return requestJson<CalibrationSessionResponse>(`/calibration/sessions/${sessionId}`)
  },

  prepareCalibrationTake(sessionId: string): Promise<CalibrationSessionResponse> {
    return requestJson<CalibrationSessionResponse>(`/calibration/sessions/${sessionId}/takes/prepare`, {
      method: 'POST',
    })
  },

  startCalibrationTake(sessionId: string): Promise<CalibrationSessionResponse> {
    return requestJson<CalibrationSessionResponse>(`/calibration/sessions/${sessionId}/takes/start`, {
      method: 'POST',
    })
  },

  stopCalibrationTake(sessionId: string): Promise<CalibrationSessionResponse> {
    return requestJson<CalibrationSessionResponse>(`/calibration/sessions/${sessionId}/takes/stop`, {
      method: 'POST',
    })
  },

  acceptCalibrationTake(sessionId: string): Promise<CalibrationSessionResponse> {
    return requestJson<CalibrationSessionResponse>(`/calibration/sessions/${sessionId}/takes/accept`, {
      method: 'POST',
    })
  },

  discardCalibrationTake(sessionId: string): Promise<CalibrationSessionResponse> {
    return requestJson<CalibrationSessionResponse>(`/calibration/sessions/${sessionId}/takes/discard`, {
      method: 'POST',
    })
  },

  completeCalibrationSession(sessionId: string): Promise<CalibrationSessionResponse> {
    return requestJson<CalibrationSessionResponse>(`/calibration/sessions/${sessionId}/complete`, {
      method: 'POST',
    })
  },

  applyCalibrationSession(sessionId: string): Promise<CalibrationApplyResponse> {
    return requestJson<CalibrationApplyResponse>(`/calibration/sessions/${sessionId}/apply`, {
      method: 'POST',
    })
  },

  rollbackCalibrationSession(sessionId: string): Promise<CalibrationRollbackResponse> {
    return requestJson<CalibrationRollbackResponse>(`/calibration/sessions/${sessionId}/rollback`, {
      method: 'POST',
    })
  },

  cancelCalibrationSession(sessionId: string): Promise<CalibrationSessionResponse> {
    return requestJson<CalibrationSessionResponse>(`/calibration/sessions/${sessionId}/cancel`, {
      method: 'POST',
    })
  },

  getGestureStatus(): Promise<GestureStatusResponse> {
    return requestJson<GestureStatusResponse>('/gestures/status')
  },

  getGestureDevices(): Promise<GestureCameraListResponse> {
    return requestJson<GestureCameraListResponse>('/gestures/devices')
  },

  startGestures(cameraIndex = 0): Promise<GestureStatusResponse> {
    return requestJson<GestureStatusResponse>('/gestures/start', {
      method: 'POST',
      body: JSON.stringify({ camera_index: cameraIndex }),
    })
  },

  stopGestures(): Promise<GestureStatusResponse> {
    return requestJson<GestureStatusResponse>('/gestures/stop', {
      method: 'POST',
    })
  },

  getGestureFrame(): Promise<GestureFrameResponse> {
    return requestJson<GestureFrameResponse>('/gestures/frame')
  },

  getLedStatus(): Promise<LEDStateResponse> {
    return requestJson<LEDStateResponse>('/led/status')
  },

  setLedColor(payload: { red: number; green: number; blue: number }): Promise<LEDStateResponse> {
    return requestJson<LEDStateResponse>('/led/color', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  setLedBrightness(brightness: number): Promise<LEDStateResponse> {
    return requestJson<LEDStateResponse>('/led/brightness', {
      method: 'POST',
      body: JSON.stringify({ brightness }),
    })
  },

  getVoiceStatus(): Promise<VoiceStatusResponse> {
    return requestJson<VoiceStatusResponse>('/voice/status')
  },

  getVoiceDevices(): Promise<VoiceInputDeviceListResponse> {
    return requestJson<VoiceInputDeviceListResponse>('/voice/devices')
  },

  startVoice(deviceIndex = -1): Promise<VoiceStatusResponse> {
    return requestJson<VoiceStatusResponse>('/voice/start', {
      method: 'POST',
      body: JSON.stringify({ device_index: deviceIndex }),
    })
  },

  stopVoice(): Promise<VoiceStatusResponse> {
    return requestJson<VoiceStatusResponse>('/voice/stop', {
      method: 'POST',
    })
  },

  getMusicalAudioStatus(): Promise<MusicalAudioStatusResponse> {
    return requestJson<MusicalAudioStatusResponse>('/musical-audio/status')
  },

  getMusicalAudioDevices(): Promise<MusicalAudioInputDeviceListResponse> {
    return requestJson<MusicalAudioInputDeviceListResponse>('/musical-audio/devices')
  },

  startMusicalAudio(deviceIndex = -1): Promise<MusicalAudioStatusResponse> {
    return requestJson<MusicalAudioStatusResponse>('/musical-audio/start', {
      method: 'POST',
      body: JSON.stringify({ device_index: deviceIndex }),
    })
  },

  stopMusicalAudio(): Promise<MusicalAudioStatusResponse> {
    return requestJson<MusicalAudioStatusResponse>('/musical-audio/stop', {
      method: 'POST',
    })
  },
}