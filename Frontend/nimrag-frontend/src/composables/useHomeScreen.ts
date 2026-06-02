import { ref, onBeforeUnmount } from 'vue'
import { buildApiUrl } from '../services/apiConfig'
import { useGestureFrameStream } from '../services/gestureFrameStream'

export interface BackendCamera {
  index: number
  name: string
  available: boolean
}

export function useHomeScreen() {
  const cameras = ref<BackendCamera[]>([])
  const currentIndex = ref(0)
  const error = ref<string | null>(null)
  const loading = ref(true)
  const slideDirection = ref<'up' | 'down' | null>(null)

  const { frameUrl, start: startStream, stop: stopStream } = useGestureFrameStream()

  async function fetchCameraList(): Promise<void> {
    try {
      const res = await fetch(buildApiUrl('gestures/devices'))
      if (!res.ok) return
      const data = (await res.json()) as { devices: BackendCamera[] }
      cameras.value = (data.devices ?? []).filter((d) => d.available)
    } catch {
      cameras.value = []
    }
  }

  async function restartWithCamera(cameraIndex: number): Promise<void> {
    loading.value = true
    try {
      await fetch(buildApiUrl('gestures/stop'), { method: 'POST' })
      await fetch(buildApiUrl('gestures/start'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_index: cameraIndex }),
      })
    } catch {
      error.value = 'Kamera konnte nicht gewechselt werden.'
    }
  }

  async function navigateCamera(direction: 'up' | 'down'): Promise<void> {
    if (cameras.value.length <= 1) return
    slideDirection.value = direction
    const total = cameras.value.length
    const next =
      direction === 'down'
        ? (currentIndex.value + 1) % total
        : (currentIndex.value - 1 + total) % total
    currentIndex.value = next
    await restartWithCamera(cameras.value[next]!.index)
    setTimeout(() => {
      slideDirection.value = null
      loading.value = false
    }, 800)
  }

  async function initializeCamera(): Promise<void> {
    loading.value = true
    error.value = null

    await fetchCameraList()

    let cameraIndex = cameras.value[0]?.index ?? 0
    let needsRestart = false

    try {
      const statusRes = await fetch(buildApiUrl('gestures/status'))
      if (!statusRes.ok) {
        needsRestart = true
      } else {
        const status = (await statusRes.json()) as { running: boolean; camera_index: number | null }
        if (!status.running) {
          needsRestart = true
        } else {
          // Sync frontend index to the camera the backend is actually using
          if (status.camera_index !== null) {
            const idx = cameras.value.findIndex((c) => c.index === status.camera_index)
            if (idx !== -1) {
              currentIndex.value = idx
              cameraIndex = cameras.value[idx]!.index
            }
          }
          // Restart if the last frame is stale (camera frozen)
          const frameRes = await fetch(buildApiUrl('gestures/frame'))
          if (!frameRes.ok) {
            needsRestart = true
          } else {
            const frame = (await frameRes.json()) as { image: string; frame_age_ms: number | null }
            if (frame.frame_age_ms !== null && frame.frame_age_ms > 2000) {
              needsRestart = true
            }
          }
        }
      }
    } catch {
      needsRestart = true
    }

    if (needsRestart) {
      try { await fetch(buildApiUrl('gestures/stop'), { method: 'POST' }) } catch { /* ignore */ }
      try {
        await fetch(buildApiUrl('gestures/start'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ camera_index: cameraIndex }),
        })
      } catch { /* ignore */ }
    }

    startStream()
    loading.value = false
  }

  function stop(): void {
    stopStream()
  }

  onBeforeUnmount(stop)

  return {
    cameras,
    currentIndex,
    frameUrl,
    error,
    loading,
    slideDirection,
    initializeCamera,
    navigateCamera,
    stopStream: stop,
  }
}
