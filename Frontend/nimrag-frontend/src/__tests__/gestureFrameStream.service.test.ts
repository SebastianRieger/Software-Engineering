import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'

vi.mock('@/services/apiConfig', () => ({
  buildApiUrl: (path: string) => `http://localhost:8000/api/v1/${path}`,
}))

const mockFetch = vi.fn()
global.fetch = mockFetch
let visibilityState: 'visible' | 'hidden' = 'visible'

Object.defineProperty(document, 'visibilityState', {
  configurable: true,
  get: () => visibilityState,
})

describe('gestureFrameStream service', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    visibilityState = 'visible'
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ image: 'data:image/jpeg;base64,abc' }),
    })
  })

  afterEach(async () => {
    // re-import to reset module-level state between tests
    vi.resetModules()
    vi.useRealTimers()
    mockFetch.mockReset()
  })

  it('start() initiates polling and stop() clears it', async () => {
    const { useGestureFrameStream } = await import('@/services/gestureFrameStream')
    const { frameUrl, start, stop } = useGestureFrameStream()

    start()
    await flushPromises()
    expect(mockFetch).toHaveBeenCalled()
    expect(frameUrl.value).toBe('data:image/jpeg;base64,abc')

    stop()
    mockFetch.mockClear()
    vi.advanceTimersByTime(200)
    expect(mockFetch).not.toHaveBeenCalled()
    expect(frameUrl.value).toBeNull()
  })

  it('stop() before refCount reaches 0 keeps the stream running', async () => {
    const { useGestureFrameStream } = await import('@/services/gestureFrameStream')
    const a = useGestureFrameStream()
    const b = useGestureFrameStream()

    a.start()
    b.start()
    await flushPromises()

    b.stop()
    mockFetch.mockClear()
    vi.advanceTimersByTime(100)
    // one consumer still active, polling continues
    expect(mockFetch).toHaveBeenCalled()

    a.stop()
  })

  it('handles fetch errors gracefully', async () => {
    mockFetch.mockRejectedValue(new Error('network error'))
    const { useGestureFrameStream } = await import('@/services/gestureFrameStream')
    const { start, stop } = useGestureFrameStream()

    start()
    await flushPromises()
    // no throw — errors are swallowed
    stop()
  })

  it('handles non-ok responses gracefully', async () => {
    mockFetch.mockResolvedValue({ ok: false })
    const { useGestureFrameStream } = await import('@/services/gestureFrameStream')
    const { frameUrl, start, stop } = useGestureFrameStream()

    start()
    await flushPromises()
    expect(frameUrl.value).toBeNull()
    stop()
  })

  it('pauses polling while the tab is hidden and resumes on visibilitychange', async () => {
    visibilityState = 'hidden'
    const { useGestureFrameStream } = await import('@/services/gestureFrameStream')
    const { start, stop } = useGestureFrameStream()

    start()
    await flushPromises()
    expect(mockFetch).not.toHaveBeenCalled()

    visibilityState = 'visible'
    document.dispatchEvent(new Event('visibilitychange'))
    await flushPromises()

    expect(mockFetch).toHaveBeenCalled()
    stop()
  })

  it('clears polling when tab becomes hidden while stream is active', async () => {
    const { useGestureFrameStream } = await import('@/services/gestureFrameStream')
    const { start, stop } = useGestureFrameStream()

    start()
    await flushPromises()
    expect(mockFetch).toHaveBeenCalled()

    mockFetch.mockClear()
    visibilityState = 'hidden'
    document.dispatchEvent(new Event('visibilitychange'))

    vi.advanceTimersByTime(200)
    expect(mockFetch).not.toHaveBeenCalled()

    stop()
  })

  it('stop() is idempotent when called more times than start()', async () => {
    const { useGestureFrameStream } = await import('@/services/gestureFrameStream')
    const { start, stop } = useGestureFrameStream()

    start()
    await flushPromises()
    stop()
    expect(() => stop()).not.toThrow()
  })
})
