import { ref, type Ref } from 'vue'
import { buildApiUrl } from './apiConfig'

const POLL_MS = 66 // ~15 fps

const _frameUrl: Ref<string | null> = ref(null)
let _timer: ReturnType<typeof setInterval> | null = null
let _refCount = 0

async function _fetchFrame(): Promise<void> {
  try {
    const res = await fetch(buildApiUrl('gestures/frame'))
    if (!res.ok) return
    const data = (await res.json()) as { image: string }
    _frameUrl.value = data.image
  } catch {
    // ignore – polling errors are transient
  }
}

export function useGestureFrameStream() {
  function start(): void {
    _refCount++
    if (_timer === null) {
      void _fetchFrame()
      _timer = setInterval(() => { void _fetchFrame() }, POLL_MS)
    }
  }

  function stop(): void {
    _refCount = Math.max(0, _refCount - 1)
    if (_refCount === 0 && _timer !== null) {
      clearInterval(_timer)
      _timer = null
      _frameUrl.value = null
    }
  }

  return {
    frameUrl: _frameUrl as Ref<string | null>,
    start,
    stop,
  }
}
