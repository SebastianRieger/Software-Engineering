import { ref, watch, onBeforeUnmount } from 'vue'
import { buildApiUrl } from '../services/apiConfig'
import { useGestureFrameStream } from '../services/gestureFrameStream'
import { warnDevOnce } from '../utils/devWarnings'

export interface BackendCamera {
  index: number
  name: string
  available: boolean
}

interface GestureStatusResponse {
  running: boolean
  camera_index: number | null
  last_error?: string | null
}

interface GestureFrameResponse {
  image?: string
  frame_age_ms: number | null
}

export type HomeScreenState = 'idle' | 'loading' | 'ready' | 'error' | 'empty'

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
    // fall through to the provided fallback below
  }

  return fallback
}

export function useHomeScreen() {
  const cameras = ref<BackendCamera[]>([])
  const currentIndex = ref(0)
  const error = ref<string | null>(null)
  const loading = ref(true)
  const slideDirection = ref<'up' | 'down' | null>(null)
  const state = ref<HomeScreenState>('idle')
  const isHomeActive = ref(false)
  const isCameraInitialized = ref(false)
  const isStreamRunning = ref(false)

  const { frameUrl, start: startStream, stop: stopStream, refreshFrame } = useGestureFrameStream()

  function syncState(): void {
    if (error.value) {
      state.value = 'error'
      return
    }

    if (loading.value) {
      state.value = 'loading'
      return
    }

    if (frameUrl.value) {
      state.value = 'ready'
      return
    }

    state.value = 'empty'
  }

  function syncStreamState(): void {
    if (!isCameraInitialized.value) {
      return
    }

    const shouldStream = isHomeActive.value && cameras.value.length > 0 && error.value === null

    if (shouldStream && !isStreamRunning.value) {
      startStream()
      isStreamRunning.value = true
      return
    }

    if (!shouldStream && isStreamRunning.value) {
      stopStream()
      isStreamRunning.value = false
    }
  }

  async function fetchJson<T>(
    path: string,
    init: RequestInit | undefined,
    fallbackMessage: string,
  ): Promise<T> {
    const res = await fetch(buildApiUrl(path), init)
    if (!res.ok) {
      throw new Error(await readErrorMessage(res, fallbackMessage))
    }

    return (await res.json()) as T
  }

  async function fetchCameraList(): Promise<void> {
    const data = await fetchJson<{ devices: BackendCamera[] }>(
      'gestures/devices',
      undefined,
      'Kameraliste konnte nicht geladen werden.',
    )
    cameras.value = (data.devices ?? []).filter((device) => device.available)
  }

  async function restartWithCamera(cameraIndex: number): Promise<void> {
    await fetchJson<GestureStatusResponse>(
      'gestures/stop',
      { method: 'POST' },
      'Kamera konnte nicht gestoppt werden.',
    )

    const status = await fetchJson<GestureStatusResponse>(
      'gestures/start',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_index: cameraIndex }),
      },
      'Kamera konnte nicht gestartet werden.',
    )

    if (!status.running) {
      throw new Error(status.last_error ?? 'Kamera konnte nicht gestartet werden.')
    }
  }

  async function navigateCamera(direction: 'up' | 'down'): Promise<void> {
    if (cameras.value.length <= 1) return

    slideDirection.value = direction
    loading.value = true
    error.value = null
    syncState()

    const total = cameras.value.length
    const next =
      direction === 'down'
        ? (currentIndex.value + 1) % total
        : (currentIndex.value - 1 + total) % total

    try {
      await restartWithCamera(cameras.value[next]!.index)
      currentIndex.value = next
      if (isHomeActive.value) {
        await refreshFrame()
      }
    } catch (err) {
      error.value = toErrorMessage(err, 'Kamera konnte nicht gewechselt werden.')
      warnDevOnce('camera', error.value, err)
    } finally {
      window.setTimeout(() => {
        slideDirection.value = null
        loading.value = false
        syncState()
      }, 800)
    }
  }

  async function initializeCamera(): Promise<void> {
    loading.value = true
    error.value = null
    syncState()

    try {
      await fetchCameraList()

      if (cameras.value.length === 0) {
        isCameraInitialized.value = true
        syncStreamState()
        return
      }

      let cameraIndex = cameras.value[0]!.index
      let needsRestart = false

      const status = await fetchJson<GestureStatusResponse>(
        'gestures/status',
        undefined,
        'Kamerastatus konnte nicht geladen werden.',
      )

      if (!status.running) {
        needsRestart = true
      } else {
        if (status.camera_index !== null) {
          const idx = cameras.value.findIndex((camera) => camera.index === status.camera_index)
          if (idx !== -1) {
            currentIndex.value = idx
            cameraIndex = cameras.value[idx]!.index
          }
        }

        try {
          const frame = await fetchJson<GestureFrameResponse>(
            'gestures/frame',
            undefined,
            'Kamerabild konnte nicht geladen werden.',
          )
          if (frame.frame_age_ms !== null && frame.frame_age_ms > 2000) {
            needsRestart = true
          }
        } catch (err) {
          needsRestart = true
          warnDevOnce('camera', 'Kamerabild musste neu initialisiert werden.', err)
        }
      }

      if (needsRestart) {
        await restartWithCamera(cameraIndex)
      }

      isCameraInitialized.value = true
      syncStreamState()

      if (isHomeActive.value) {
        await refreshFrame()
      }
    } catch (err) {
      error.value = toErrorMessage(err, 'Kamera konnte nicht initialisiert werden.')
      warnDevOnce('camera', error.value, err)
      if (isStreamRunning.value) {
        stopStream()
        isStreamRunning.value = false
      }
      frameUrl.value = null
    } finally {
      loading.value = false
      syncState()
    }
  }

  function setHomeActive(active: boolean): void {
    isHomeActive.value = active
    syncStreamState()
  }

  function stop(): void {
    isHomeActive.value = false
    if (isStreamRunning.value) {
      stopStream()
      isStreamRunning.value = false
    }
  }

  watch([frameUrl, error, loading], syncState, { immediate: true })

  onBeforeUnmount(stop)

  return {
    cameras,
    currentIndex,
    frameUrl,
    error,
    loading,
    state,
    slideDirection,
    initializeCamera,
    navigateCamera,
    setHomeActive,
    stopStream: stop,
  }
}
