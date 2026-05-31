import { ref, onBeforeUnmount } from 'vue'
import { buildApiUrl } from '../services/apiConfig'
import { backendReachability } from '../services/backendReachability'

export interface BackendCamera {
  index: number
  name: string
  available: boolean
}

const POLL_MS = 66 // ~15fps
const RETRY_MS = 1500

export function useHomeScreen() {
  const cameras = ref<BackendCamera[]>([])
  const currentIndex = ref(0)
  const frameUrl = ref<string | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(true)
  const slideDirection = ref<'up' | 'down' | null>(null)

  let pollTimer: ReturnType<typeof setInterval> | null = null
  let retryTimer: ReturnType<typeof setTimeout> | null = null
  let bootstrapInFlight = false

  function clearPollTimer(): void {
    if (pollTimer !== null) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function clearRetryTimer(): void {
    if (retryTimer !== null) {
      clearTimeout(retryTimer)
      retryTimer = null
    }
  }

  function scheduleRetry(): void {
    if (retryTimer !== null) return
    const delayMs = Math.max(RETRY_MS, backendReachability.getRetryDelayMs())
    retryTimer = setTimeout(() => {
      retryTimer = null
      void initializeCamera()
    }, delayMs)
  }

  function ensurePolling(): void {
    if (pollTimer !== null) return
    pollTimer = setInterval(() => {
      void pollFrame()
    }, POLL_MS)
  }

  async function fetchFrame(): Promise<boolean> {
    try {
      const res = await fetch(buildApiUrl('gestures/frame'))
      if (!res.ok) {
        frameUrl.value = null
        return false
      }
      const data = (await res.json()) as { image: string }
      backendReachability.markReachable()
      frameUrl.value = data.image
      if (loading.value) loading.value = false
      error.value = null
      return true
    } catch (cameraError) {
      backendReachability.noteRequestFailure(cameraError)
      frameUrl.value = null
      return false
    }
  }

  async function pollFrame(): Promise<void> {
    const hasFrame = await fetchFrame()
    if (hasFrame) {
      clearRetryTimer()
      return
    }

    clearPollTimer()
    error.value = 'Backend-Kamera nicht erreichbar.'
    scheduleRetry()
  }

  async function fetchCameraList(): Promise<void> {
    try {
      const res = await fetch(buildApiUrl('gestures/devices'))
      if (!res.ok) return
      const data = (await res.json()) as { devices: BackendCamera[] }
      backendReachability.markReachable()
      cameras.value = (data.devices ?? []).filter((d) => d.available)
    } catch (cameraError) {
      backendReachability.noteRequestFailure(cameraError)
      cameras.value = []
    }
  }

  async function restartWithCamera(cameraIndex: number): Promise<void> {
    loading.value = true
    try {
      await fetch(buildApiUrl('gestures/stop'), { method: 'POST' })
      const response = await fetch(buildApiUrl('gestures/start'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_index: cameraIndex }),
      })
      if (!response.ok) {
        throw new Error('restart failed')
      }
      backendReachability.markReachable()
      clearRetryTimer()
      ensurePolling()
      void pollFrame()
    } catch (cameraError) {
      backendReachability.noteRequestFailure(cameraError)
      error.value = 'Kamera konnte nicht gewechselt werden.'
      clearPollTimer()
      scheduleRetry()
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
    if (bootstrapInFlight) return
    bootstrapInFlight = true
    clearPollTimer()
    loading.value = true
    error.value = null

    const reachable = await backendReachability.requestAvailabilityCheck()
    if (!reachable) {
      error.value = 'Backend-Kamera nicht erreichbar.'
      loading.value = false
      bootstrapInFlight = false
      scheduleRetry()
      return
    }

    let cameraIndex = currentIndex.value
    let status: { running: boolean; camera_index: number | null } | null = null

    try {
      const statusRes = await fetch(buildApiUrl('gestures/status'))
      if (!statusRes.ok) {
        throw new Error('status unavailable')
      } else {
        status = (await statusRes.json()) as { running: boolean; camera_index: number | null }
        backendReachability.markReachable()
      }
    } catch (statusError) {
      backendReachability.noteRequestFailure(statusError)
      error.value = 'Backend-Kamera nicht erreichbar.'
      loading.value = false
      bootstrapInFlight = false
      scheduleRetry()
      return
    }

    await fetchCameraList()

    if (status.camera_index !== null) {
      const idx = cameras.value.findIndex((c) => c.index === status.camera_index)
      if (idx !== -1) {
        currentIndex.value = idx
        cameraIndex = cameras.value[idx]!.index
      } else {
        cameraIndex = status.camera_index
      }
    } else {
      cameraIndex = cameras.value[currentIndex.value]?.index ?? cameras.value[0]?.index ?? 0
    }

    let needsRestart = !status.running

    if (status.running) {
      // Restart if the last frame is stale (camera frozen) or unavailable.
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

    if (needsRestart) {
      try { await fetch(buildApiUrl('gestures/stop'), { method: 'POST' }) } catch { /* ignore */ }
      try {
        const response = await fetch(buildApiUrl('gestures/start'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ camera_index: cameraIndex }),
        })
        if (!response.ok) {
          throw new Error('start failed')
        }
      } catch { /* ignore */ }
    }

    const hasFrame = await fetchFrame()
    if (hasFrame) {
      clearRetryTimer()
      ensurePolling()
    } else {
      error.value = 'Backend-Kamera nicht erreichbar.'
      scheduleRetry()
    }
    loading.value = false
    bootstrapInFlight = false
  }

  function stopStream(): void {
    clearPollTimer()
    clearRetryTimer()
    frameUrl.value = null
  }

  onBeforeUnmount(stopStream)

  return {
    cameras,
    currentIndex,
    frameUrl,
    error,
    loading,
    slideDirection,
    initializeCamera,
    navigateCamera,
    stopStream,
  }
}
