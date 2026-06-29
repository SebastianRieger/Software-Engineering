import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useMicrophoneSelection } from '@/composables/useMicrophoneSelection'

vi.mock('@/services/apiConfig', () => ({
  buildApiUrl: (path: string) => `/api/${path}`,
}))

function jsonResponse(data: unknown, ok = true): Response {
  return {
    ok,
    json: async () => data,
  } as Response
}

describe('useMicrophoneSelection', () => {
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

  it('fetchStatus updates enabled, device_name and last_error from the backend', async () => {
    const selection = useMicrophoneSelection()
    selection.error.value = 'stale frontend error'

    mockFetch.mockResolvedValueOnce(jsonResponse({
      message: 'Voice status',
      available: true,
      enabled: false,
      running: false,
      device_index: 3,
      device_name: 'Desk Mic',
      last_error: 'VOICE_ENABLED=False',
    }))

    const status = await selection.fetchStatus()

    expect(status?.enabled).toBe(false)
    expect(selection.isEnabled.value).toBe(false)
    expect(selection.deviceName.value).toBe('Desk Mic')
    expect(selection.lastBackendError.value).toBe('VOICE_ENABLED=False')
    expect(selection.error.value).toBeNull()
  })

  it('returns a structured failure and keeps running=false when voice/start fails', async () => {
    const selection = useMicrophoneSelection()

    mockFetch
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

    const result = await selection.selectDevice(2)

    expect(result.ok).toBe(false)
    expect(result.message).toBe('PortAudio denied')
    expect(result.status?.running).toBe(false)
    expect(selection.isRunning.value).toBe(false)
    expect(selection.error.value).toBeNull()
    expect(selection.lastBackendError.value).toBe('PortAudio denied')
  })

  it('only reports success after the backend confirms running=true', async () => {
    const selection = useMicrophoneSelection()

    mockFetch
      .mockResolvedValueOnce(jsonResponse({ message: 'Voice stopped' }))
      .mockResolvedValueOnce(jsonResponse({
        message: 'Voice starting',
        available: true,
        enabled: true,
        running: false,
        device_index: 2,
        device_name: 'USB Mic',
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

    const resultPromise = selection.selectDevice(2)
    await vi.advanceTimersByTimeAsync(250)
    const result = await resultPromise

    expect(result.ok).toBe(true)
    expect(result.status?.running).toBe(true)
    expect(selection.isRunning.value).toBe(true)
    expect(selection.activeDeviceIndex.value).toBe(2)
    expect(selection.deviceName.value).toBe('USB Mic')
    expect(selection.error.value).toBeNull()
  })
})
