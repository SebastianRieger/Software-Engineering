import { ref, type Ref } from 'vue'
import { buildApiUrl } from './apiConfig'

const POLL_MS = 66 // ~15 fps

const _frameUrl: Ref<string | null> = ref(null)
let _timer: ReturnType<typeof setInterval> | null = null
let _refCount = 0
let _isVisibilityListenerAttached = false

function isDocumentVisible(): boolean {
  return typeof document === 'undefined' || document.visibilityState === 'visible'
}

function clearPolling(): void {
  if (_timer !== null) {
    clearInterval(_timer)
    _timer = null
  }
}

async function _fetchFrame(): Promise<boolean> {
  if (!isDocumentVisible()) {
    return false
  }

  try {
    const res = await fetch(buildApiUrl('gestures/frame'))
    if (!res.ok) return false
    const data = (await res.json()) as { image?: string }
    _frameUrl.value = typeof data.image === 'string' ? data.image : null
    return _frameUrl.value !== null
  } catch {
    // ignore – polling errors are transient
    return false
  }
}

function ensurePolling(): void {
  if (_refCount <= 0 || _timer !== null || !isDocumentVisible()) {
    return
  }

  void _fetchFrame()
  _timer = setInterval(() => { void _fetchFrame() }, POLL_MS)
}

function handleVisibilityChange(): void {
  if (_refCount <= 0) {
    return
  }

  if (!isDocumentVisible()) {
    clearPolling()
    return
  }

  ensurePolling()
}

function attachVisibilityListener(): void {
  if (_isVisibilityListenerAttached || typeof document === 'undefined') {
    return
  }

  document.addEventListener('visibilitychange', handleVisibilityChange)
  _isVisibilityListenerAttached = true
}

function detachVisibilityListener(): void {
  if (!_isVisibilityListenerAttached || typeof document === 'undefined') {
    return
  }

  document.removeEventListener('visibilitychange', handleVisibilityChange)
  _isVisibilityListenerAttached = false
}

export function useGestureFrameStream() {
  function start(): void {
    _refCount++
    attachVisibilityListener()
    ensurePolling()
  }

  function stop(): void {
    _refCount = Math.max(0, _refCount - 1)
    if (_refCount === 0) {
      clearPolling()
      detachVisibilityListener()
      _frameUrl.value = null
    }
  }

  return {
    frameUrl: _frameUrl as Ref<string | null>,
    start,
    stop,
    refreshFrame: _fetchFrame,
  }
}
