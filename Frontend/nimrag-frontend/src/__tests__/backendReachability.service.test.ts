import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMock = vi.fn()

async function loadBackendReachability() {
  vi.resetModules()
  return import('@/services/backendReachability')
}

describe('backendReachability service', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.resetModules()
  })

  it('caches a successful availability probe', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) })

    const { backendReachability } = await loadBackendReachability()

    await expect(backendReachability.requestAvailabilityCheck()).resolves.toBe(true)
    await expect(backendReachability.requestAvailabilityCheck()).resolves.toBe(true)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/system/status'), expect.any(Object))
  })

  it('backs off failed probes and suppresses duplicate checks during cooldown', async () => {
    fetchMock.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })

    const { backendReachability } = await loadBackendReachability()

    await expect(backendReachability.requestAvailabilityCheck()).resolves.toBe(false)
    await expect(backendReachability.requestAvailabilityCheck()).resolves.toBe(false)

    expect(fetchMock).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(1499)
    await expect(backendReachability.requestAvailabilityCheck()).resolves.toBe(false)
    expect(fetchMock).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(1)
    await expect(backendReachability.requestAvailabilityCheck()).resolves.toBe(false)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})