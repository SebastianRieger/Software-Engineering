import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useHomeScreen } from '@/composables/useHomeScreen'

const streamMock = vi.hoisted(() => ({
  frameUrl: { value: null, __v_isRef: true } as { value: string | null; __v_isRef: true },
  start: vi.fn(),
  stop: vi.fn(),
  refreshFrame: vi.fn().mockResolvedValue(true),
}))

vi.mock('@/services/apiConfig', () => ({
  buildApiUrl: (path: string) => `/api/${path}`,
}))

vi.mock('@/services/gestureFrameStream', () => ({
  useGestureFrameStream: () => streamMock,
}))

function jsonResponse(data: unknown, ok = true): Response {
  return {
    ok,
    json: async () => data,
  } as Response
}

function mountHarness() {
  let home: ReturnType<typeof useHomeScreen> | null = null

  const wrapper = mount(defineComponent({
    setup() {
      home = useHomeScreen()
      return () => null
    },
  }))

  return {
    wrapper,
    home: home!,
  }
}

describe('useHomeScreen', () => {
  const mockFetch = vi.fn()

  beforeEach(() => {
    streamMock.frameUrl.value = null
    streamMock.start.mockReset()
    streamMock.stop.mockReset()
    streamMock.refreshFrame.mockReset()
    streamMock.refreshFrame.mockResolvedValue(true)
    mockFetch.mockReset()
    vi.stubGlobal('fetch', mockFetch)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('surfaces a visible error when gestures/status fails', async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse({
        devices: [{ index: 0, name: 'Front Cam', available: true }],
      }))
      .mockResolvedValueOnce(jsonResponse({ detail: 'Gesture backend offline' }, false))

    const { wrapper, home } = mountHarness()
    home.setHomeActive(true)

    await home.initializeCamera()
    await flushPromises()

    expect(home.error.value).toBe('Gesture backend offline')
    expect(home.state.value).toBe('error')
    expect(streamMock.start).not.toHaveBeenCalled()

    wrapper.unmount()
  })

  it('surfaces a visible error when gestures/start fails', async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse({
        devices: [{ index: 0, name: 'Front Cam', available: true }],
      }))
      .mockResolvedValueOnce(jsonResponse({ running: false, camera_index: null }))
      .mockResolvedValueOnce(jsonResponse({ running: false }))
      .mockResolvedValueOnce(jsonResponse({ detail: 'Camera busy' }, false))

    const { wrapper, home } = mountHarness()
    home.setHomeActive(true)

    await home.initializeCamera()
    await flushPromises()

    expect(home.error.value).toBe('Camera busy')
    expect(home.state.value).toBe('error')
    expect(streamMock.start).not.toHaveBeenCalled()

    wrapper.unmount()
  })

  it('stops polling when leaving home and restarts when returning', async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse({
        devices: [{ index: 7, name: 'Front Cam', available: true }],
      }))
      .mockResolvedValueOnce(jsonResponse({ running: true, camera_index: 7 }))
      .mockResolvedValueOnce(jsonResponse({ image: 'data:image/jpeg;base64,abc', frame_age_ms: 120 }))

    const { wrapper, home } = mountHarness()
    home.setHomeActive(true)

    await home.initializeCamera()
    await flushPromises()

    expect(streamMock.start).toHaveBeenCalledOnce()
    expect(streamMock.refreshFrame).toHaveBeenCalledOnce()

    home.setHomeActive(false)
    expect(streamMock.stop).toHaveBeenCalledOnce()

    home.setHomeActive(true)
    expect(streamMock.start).toHaveBeenCalledTimes(2)

    wrapper.unmount()
  })
})
