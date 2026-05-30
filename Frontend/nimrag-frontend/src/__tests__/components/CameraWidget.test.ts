import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import CameraWidget from '@/components/widgets/CameraWidget.vue'

const fetchMock = vi.fn()

beforeEach(() => {
  vi.useFakeTimers()
  fetchMock.mockReset()
  fetchMock.mockImplementation((url: string) => {
    if (url.endsWith('/gestures/status')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ running: true, camera_name: 'Backend Camera' }),
      })
    }
    if (url.endsWith('/gestures/frame')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ image: 'data:image/jpeg;base64,abc', frame_age_ms: 42 }),
      })
    }
    return Promise.resolve({ ok: false, json: () => Promise.resolve({}) })
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('CameraWidget', () => {
  it('renders the backend camera frame on mount', async () => {
    const wrapper = mount(CameraWidget)
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/gestures/status'))
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/gestures/frame'))
    expect(wrapper.find('img').attributes('src')).toBe('data:image/jpeg;base64,abc')
    expect(wrapper.text()).toContain('Backend Camera')
    expect(wrapper.text()).toContain('42 ms')
  })

  it('polls backend frames and stops polling on unmount', async () => {
    const wrapper = mount(CameraWidget)
    await flushPromises()

    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes('/gestures/frame'))).toHaveLength(1)

    vi.advanceTimersByTime(250)
    await flushPromises()

    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes('/gestures/frame'))).toHaveLength(2)

    wrapper.unmount()
    vi.advanceTimersByTime(250)
    await flushPromises()

    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes('/gestures/frame'))).toHaveLength(2)
  })

  it('does not use browser media devices', async () => {
    const getUserMedia = vi.fn()
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia },
    })

    mount(CameraWidget)
    await flushPromises()

    expect(getUserMedia).not.toHaveBeenCalled()
  })
})