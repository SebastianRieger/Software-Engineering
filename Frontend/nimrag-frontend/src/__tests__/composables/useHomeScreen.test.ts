import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useHomeScreen } from '@/composables/useHomeScreen'
import { resetBackendReachabilityForTests } from '@/services/backendReachability'

const fetchMock = vi.fn()

const Host = defineComponent({
  template: '<div />',
  setup() {
    return useHomeScreen()
  },
})

describe('useHomeScreen', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    fetchMock.mockReset()
    resetBackendReachabilityForTests()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('backs off retries when the backend is unavailable', async () => {
    fetchMock.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })

    const wrapper = mount(Host)
    await wrapper.vm.initializeCamera()
    await flushPromises()

    const initialSystemStatusCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes('/system/status')).length
    expect(initialSystemStatusCalls).toBe(1)

    const initialBootstrapCalls = fetchMock.mock.calls.filter(([url]) => {
      const value = String(url)
      return value.includes('/gestures/status') || value.includes('/gestures/devices') || value.includes('/gestures/stop') || value.includes('/gestures/start') || value.includes('/gestures/frame')
    }).length
    expect(initialBootstrapCalls).toBe(0)

    vi.advanceTimersByTime(66)
    await flushPromises()

    const systemStatusCallsDuringBackoff = fetchMock.mock.calls.filter(([url]) => String(url).includes('/system/status')).length
    expect(systemStatusCallsDuringBackoff).toBe(1)

    vi.advanceTimersByTime(1500)
    await flushPromises()

    const retriedSystemStatusCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes('/system/status')).length
    expect(retriedSystemStatusCalls).toBe(2)
  })

  it('starts polling only after a frame is available', async () => {
    fetchMock.mockImplementation((url: string) => {
      if (url.endsWith('/system/status')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
      }
      if (url.endsWith('/gestures/devices')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ devices: [{ index: 0, name: 'Cam', available: true }] }) })
      }
      if (url.endsWith('/gestures/status')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ running: true, camera_index: 0 }) })
      }
      if (url.endsWith('/gestures/frame')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ image: 'data:image/jpeg;base64,ok', frame_age_ms: 10 }) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })

    const wrapper = mount(Host)
    await wrapper.vm.initializeCamera()
    await flushPromises()

    expect(wrapper.vm.frameUrl).toBe('data:image/jpeg;base64,ok')

    const initialFrameCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes('/gestures/frame')).length
    expect(initialFrameCalls).toBe(2)

    vi.advanceTimersByTime(66)
    await flushPromises()

    const polledFrameCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes('/gestures/frame')).length
    expect(polledFrameCalls).toBe(3)
  })
})