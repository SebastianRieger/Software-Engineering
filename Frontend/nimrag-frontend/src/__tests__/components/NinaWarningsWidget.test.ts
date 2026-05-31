import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'

import NinaWarningsWidget from '@/components/widgets/NinaWarningsWidget.vue'
import { loadAppConfig } from '@/composables/useAppConfig'

// Mountet das Widget mit 2×2-Kontext (full layout) als Standard
function mountWidget(options: Parameters<typeof mount>[1] = {}) {
  return mount(NinaWarningsWidget, {
    ...options,
    global: {
      provide: {
        cellId: 1,
        cellSizes: ref({ 1: 4 }),  // size 4 = 2×2 = full layout
      },
      ...(options as any).global,
    },
  })
}

vi.mock('@/composables/useAppConfig', () => ({
  loadAppConfig: vi.fn(),
}))

const mockedLoadAppConfig = vi.mocked(loadAppConfig)

const NOW = new Date('2026-05-31T12:00:00.000Z')
const TWO_HOURS_AGO  = new Date(NOW.getTime() - 2 * 60 * 60 * 1000).toISOString()
const THIRTY_MIN_AGO = new Date(NOW.getTime() - 30 * 60 * 1000).toISOString()

const WARNING_EXTREME = {
  id: 'warn-001',
  severity: 'Extreme',
  headline: 'Extreme Unwetterwarnung',
  sender_name: 'Deutscher Wetterdienst',
  event: 'Thunderstorm',
  sent: TWO_HOURS_AGO,
  msg_type: 'Alert',
}

const WARNING_MODERATE = {
  id: 'warn-002',
  severity: 'Moderate',
  headline: 'Moderate Hochwasserwarnung',
  sender_name: 'Landratsamt',
  event: 'Flood',
  sent: THIRTY_MIN_AGO,
  msg_type: 'Alert',
}

const DEFAULT_CONFIG = {
  version: 1,
  system: {
    location_name: 'Stuttgart',
    latitude: 48.7758,
    longitude: 9.1829,
    units: 'metric',
    theme: 'dark',
    weather_refresh_seconds: 900,
    updated_at: null,
  },
  widgets: {
    weather: { refresh_seconds: 900 },
    news: { ressort: null, regions: [1], refresh_seconds: 3600 },
    camera: { preferred_device_id: null, preferred_device_label: null },
    nina: { ars: '000000000000', refresh_seconds: 300 },
  },
}

function makeResponse(warnings: object[]) {
  return { ars: '000000000000', warnings, fetched_at: NOW.toISOString(), source: 'live' }
}

function mockFetch(warnings: object[], status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: status < 400,
      status,
      json: () => Promise.resolve(makeResponse(warnings)),
    }),
  )
}

function mockFetchNetworkError() {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(NOW)
  mockedLoadAppConfig.mockResolvedValue(DEFAULT_CONFIG as any)
  mockFetch([])
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  mockedLoadAppConfig.mockReset()
})

describe('NinaWarningsWidget', () => {
  it('mounts without errors', async () => {
    const wrapper = mountWidget()
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('shows loading spinner before data arrives (no prior data)', () => {
    let resolveFetch!: (v: unknown) => void
    vi.stubGlobal(
      'fetch',
      vi.fn().mockReturnValue(new Promise(r => { resolveFetch = r })),
    )
    const wrapper = mountWidget()
    expect(wrapper.find('.nina-spinner').exists()).toBe(true)
    resolveFetch({ ok: true, status: 200, json: () => Promise.resolve(makeResponse([])) })
  })

  it('shows no-warnings state when list is empty', async () => {
    mockFetch([])
    const wrapper = mountWidget()
    await flushPromises()
    expect(wrapper.text()).toContain('Keine aktuellen Warnungen')
  })

  describe('single warning', () => {
    it('shows the headline', async () => {
      mockFetch([WARNING_EXTREME])
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.text()).toContain('Extreme Unwetterwarnung')
    })

    it('shows the severity badge', async () => {
      mockFetch([WARNING_EXTREME])
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.find('.nina-badge').text()).toBe('EXTREM')
    })

    it('shows sender name', async () => {
      mockFetch([WARNING_EXTREME])
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.text()).toContain('Deutscher Wetterdienst')
    })

    it('shows event type', async () => {
      mockFetch([WARNING_EXTREME])
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.text()).toContain('Thunderstorm')
    })

    it('shows relative time (2h old → "vor 2h")', async () => {
      mockFetch([WARNING_EXTREME])
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.text()).toContain('vor 2h')
    })

    it('applies nina-widget--danger class for Extreme severity', async () => {
      mockFetch([WARNING_EXTREME])
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.find('.nina-widget').classes()).toContain('nina-widget--danger')
    })

    it('shows count label "1 Warnung"', async () => {
      mockFetch([WARNING_EXTREME])
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.text()).toContain('1 Warnung')
    })

    it('does not show pagination dots for a single warning', async () => {
      mockFetch([WARNING_EXTREME])
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.find('.nina-dots').exists()).toBe(false)
    })
  })

  describe('multiple warnings', () => {
    it('shows plural count label', async () => {
      mockFetch([WARNING_EXTREME, WARNING_MODERATE])
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.text()).toContain('2 Warnungen')
    })

    it('shows pagination dots', async () => {
      mockFetch([WARNING_EXTREME, WARNING_MODERATE])
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.find('.nina-dots').exists()).toBe(true)
      expect(wrapper.findAll('.nina-dot').length).toBe(2)
    })

    it('marks first dot as active initially', async () => {
      mockFetch([WARNING_EXTREME, WARNING_MODERATE])
      const wrapper = mountWidget()
      await flushPromises()
      const dots = wrapper.findAll('.nina-dot')
      expect(dots[0].classes()).toContain('nina-dot--active')
      expect(dots[1].classes()).not.toContain('nina-dot--active')
    })

    it('shows first warning headline initially', async () => {
      mockFetch([WARNING_EXTREME, WARNING_MODERATE])
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.text()).toContain('Extreme Unwetterwarnung')
    })
  })

  it('shows correct badge color for Moderate severity', async () => {
    mockFetch([WARNING_MODERATE])
    const wrapper = mountWidget()
    await flushPromises()
    const badge = wrapper.find('.nina-badge')
    expect(badge.text()).toBe('MITTEL')
    expect((badge.element as HTMLElement).style.backgroundColor).toBe('rgb(202, 138, 4)')
  })

  describe('error states', () => {
    it('shows HTTP 503 error message', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 503, json: vi.fn() }),
      )
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.text()).toContain('Fehler 503')
    })

    it('shows network error message on fetch failure', async () => {
      mockFetchNetworkError()
      const wrapper = mountWidget()
      await flushPromises()
      expect(wrapper.text()).toContain('Keine Verbindung')
    })
  })

  it('calls the API with the correct ARS from props', async () => {
    const customArs = '053150000000'
    mockFetch([])
    mountWidget({ props: { ars: customArs } })
    await flushPromises()
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.stringContaining(`/api/v1/nina/${customArs}`),
    )
  })

  it('calls the API with the ARS from app_config when no prop given', async () => {
    mockFetch([])
    mountWidget()
    await flushPromises()
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/nina/000000000000'),
    )
  })

  it('relative time: 30 min old warning → "vor 30 Min"', async () => {
    mockFetch([WARNING_MODERATE])
    const wrapper = mountWidget()
    await flushPromises()
    expect(wrapper.text()).toContain('vor 30 Min')
  })
})
