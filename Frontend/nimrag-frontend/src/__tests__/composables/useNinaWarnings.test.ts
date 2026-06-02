import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { useNinaWarnings, _resetNinaStateForTesting } from '@/composables/useNinaWarnings'

const mockFetch = vi.fn()
global.fetch = mockFetch

const MOCK_RESPONSE = {
  ars: '082215000000',
  warnings: [{ id: 'w1', severity: 'Minor', headline: 'Test', sender_name: 'DWD', event: null, sent: '2024-01-01T00:00:00Z', msg_type: 'Alert' }],
  fetched_at: '2024-01-01T00:00:00Z',
  source: 'live' as const,
}

beforeEach(() => {
  vi.useFakeTimers()
  _resetNinaStateForTesting()
  mockFetch.mockReset()
  mockFetch.mockResolvedValue({ ok: true, json: async () => MOCK_RESPONSE })
})

afterEach(() => {
  _resetNinaStateForTesting()
  vi.useRealTimers()
})

describe('useNinaWarnings', () => {
  it('fetches warnings on first mount', async () => {
    const { warnings, loading } = useNinaWarnings('082215000000')
    await flushPromises()
    expect(mockFetch).toHaveBeenCalledOnce()
    expect(warnings.value).toHaveLength(1)
    expect(loading.value).toBe(false)
  })

  it('handles non-ok responses', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 503 })
    const { error, warnings } = useNinaWarnings('082215000000')
    await flushPromises()
    expect(error.value).toBe('Fehler 503')
    expect(warnings.value).toHaveLength(0)
  })

  it('handles network errors', async () => {
    mockFetch.mockRejectedValue(new Error('offline'))
    const { error } = useNinaWarnings('082215000000')
    await flushPromises()
    expect(error.value).toBe('Keine Verbindung')
  })

  it('refresh() re-fetches warnings', async () => {
    const { refresh } = useNinaWarnings('082215000000')
    await flushPromises()
    mockFetch.mockClear()
    refresh()
    await flushPromises()
    expect(mockFetch).toHaveBeenCalledOnce()
  })

  it('unmount() cleans up state when last consumer leaves', async () => {
    const { unmount } = useNinaWarnings('082215000000')
    await flushPromises()
    unmount()
    mockFetch.mockClear()
    vi.advanceTimersByTime(600_000)
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('second consumer shares state and does not restart polling', async () => {
    const a = useNinaWarnings('082215000000')
    const b = useNinaWarnings('082215000000')
    await flushPromises()
    // fetch was only called once (shared state)
    expect(mockFetch).toHaveBeenCalledOnce()
    b.unmount()
    a.unmount()
  })
})
