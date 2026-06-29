import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/apiConfig', () => ({
  buildApiUrl: (path: string) => `/api/${path}`,
}))

import MicrophoneSelector from '@/components/manager/MicrophoneSelector.vue'

function jsonResponse(data: unknown, ok = true): Response {
  return {
    ok,
    json: async () => data,
  } as Response
}

describe('MicrophoneSelector', () => {
  const mockFetch = vi.fn()

  beforeEach(() => {
    vi.useFakeTimers()
    mockFetch.mockReset()
    vi.stubGlobal('fetch', mockFetch)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('keeps the panel open when device selection fails', async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse({
        devices: [
          {
            index: 2,
            name: 'USB Mic',
            max_input_channels: 1,
            default_samplerate: 48000,
            is_default: true,
          },
        ],
      }))
      .mockResolvedValueOnce(jsonResponse({
        message: 'Voice status',
        available: true,
        enabled: true,
        running: false,
        device_index: null,
        device_name: null,
        last_error: null,
      }))
      .mockResolvedValueOnce(jsonResponse({
        devices: [
          {
            index: 2,
            name: 'USB Mic',
            max_input_channels: 1,
            default_samplerate: 48000,
            is_default: true,
          },
        ],
      }))
      .mockResolvedValueOnce(jsonResponse({
        message: 'Voice status',
        available: true,
        enabled: true,
        running: false,
        device_index: null,
        device_name: null,
        last_error: null,
      }))
      .mockResolvedValueOnce(jsonResponse({ message: 'Voice stopped' }))
      .mockResolvedValueOnce(jsonResponse({ detail: 'Model missing' }, false))
      .mockResolvedValueOnce(jsonResponse({
        message: 'Voice status',
        available: true,
        enabled: true,
        running: false,
        device_index: null,
        device_name: null,
        last_error: 'PortAudio denied',
      }))

    const wrapper = mount(MicrophoneSelector)
    await flushPromises()

    await wrapper.find('.mic-trigger').trigger('click')
    await flushPromises()
    await wrapper.find('.mic-item').trigger('click')
    await flushPromises()

    expect(wrapper.find('.mic-panel').exists()).toBe(true)
    expect(wrapper.text()).toContain('PortAudio denied')

    wrapper.unmount()
  })

  it('renders backend last_error in the panel and trigger tooltip', async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse({ devices: [] }))
      .mockResolvedValueOnce(jsonResponse({
        message: 'Voice status',
        available: true,
        enabled: true,
        running: false,
        device_index: null,
        device_name: null,
        last_error: 'PortAudio denied',
      }))
      .mockResolvedValueOnce(jsonResponse({ devices: [] }))
      .mockResolvedValueOnce(jsonResponse({
        message: 'Voice status',
        available: true,
        enabled: true,
        running: false,
        device_index: null,
        device_name: null,
        last_error: 'PortAudio denied',
      }))

    const wrapper = mount(MicrophoneSelector)
    await flushPromises()

    expect(wrapper.find('.mic-trigger').attributes('title')).toBe('PortAudio denied')

    await wrapper.find('.mic-trigger').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('PortAudio denied')

    wrapper.unmount()
  })

  it('only shows the green active state when the backend reports running=true', async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse({
        devices: [
          {
            index: 2,
            name: 'USB Mic',
            max_input_channels: 1,
            default_samplerate: 48000,
            is_default: true,
          },
        ],
      }))
      .mockResolvedValueOnce(jsonResponse({
        message: 'Voice status',
        available: true,
        enabled: true,
        running: false,
        device_index: null,
        device_name: null,
        last_error: null,
      }))
      .mockResolvedValueOnce(jsonResponse({
        message: 'Voice status',
        available: true,
        enabled: true,
        running: true,
        device_index: 2,
        device_name: 'USB Mic',
        last_error: null,
      }))

    const wrapper = mount(MicrophoneSelector)
    await flushPromises()

    expect(wrapper.find('.mic-trigger').classes()).not.toContain('mic-trigger--active')
    expect(wrapper.find('.mic-active-dot').exists()).toBe(false)

    await vi.advanceTimersByTimeAsync(5000)
    await flushPromises()

    expect(wrapper.find('.mic-trigger').classes()).toContain('mic-trigger--active')
    expect(wrapper.find('.mic-active-dot').exists()).toBe(true)

    wrapper.unmount()
  })
})
