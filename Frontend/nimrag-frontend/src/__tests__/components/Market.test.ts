import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import Market from '@/components/widgets/Market.vue'
import { loadAppConfig } from '@/composables/useAppConfig'
import { getMarket } from '@/services/market'

vi.mock('@/composables/useAppConfig', () => ({
  loadAppConfig: vi.fn(),
}))

vi.mock('@/services/market', () => ({
  getMarket: vi.fn(),
}))

const mockedLoadAppConfig = vi.mocked(loadAppConfig)
const mockedGetMarket = vi.mocked(getMarket)

const makeMarketItem = (overrides: Partial<Record<string, unknown>> = {}) => ({
  id: 'AAPL',
  symbol: 'AAPL',
  name: 'Apple Inc',
  price: 189.37,
  change: 1.23,
  percent_change: 0.65,
  currency: 'USD',
  asset_type: 'stock' as const,
  ...overrides,
})

const mockMarket = (items: unknown[] = [makeMarketItem()]) => {
  mockedGetMarket.mockResolvedValue({ items: items as never, source: 'live' })
}

const defaultAppConfig = {
  version: 1,
  system: {
    location_name: 'Stuttgart',
    latitude: 48.7758,
    longitude: 9.1829,
    units: 'metric' as const,
    theme: 'dark' as const,
    weather_refresh_seconds: 900,
    updated_at: null,
  },
  widgets: {
    weather: { refresh_seconds: 900 },
    news: { ressort: null, regions: [1], refresh_seconds: 3600 },
    camera: { preferred_device_id: null, preferred_device_label: null },
    market: { symbols: ['AAPL', 'BTC/USD'], refresh_seconds: 900 },
  },
}

beforeEach(() => {
  vi.useFakeTimers()
  mockedLoadAppConfig.mockReset()
  mockedGetMarket.mockReset()
  mockedLoadAppConfig.mockResolvedValue(defaultAppConfig)
  mockMarket()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('Market widget', () => {
  it('shows loading state while fetching', () => {
    mockedGetMarket.mockReturnValue(new Promise(() => {}))
    const wrapper = mount(Market)
    expect(wrapper.text()).toContain('Lädt')
  })

  it('displays items after successful fetch', async () => {
    mockMarket([makeMarketItem({ symbol: 'AAPL', name: 'Apple Inc' })])
    const wrapper = mount(Market)
    await flushPromises()

    expect(wrapper.text()).toContain('AAPL')
    expect(wrapper.text()).not.toContain('Lädt')
  })

  it('shows error state when fetch fails with HTTP 503', async () => {
    mockedGetMarket.mockRejectedValueOnce(
      Object.assign(new Error('HTTP 503'), { status: 503 }),
    )
    const wrapper = mount(Market)
    await flushPromises()

    expect(wrapper.text()).toContain('Kurse nicht verfügbar')
  })

  it('shows error state when fetch fails with network error', async () => {
    mockedGetMarket.mockRejectedValueOnce(new Error('Network error'))
    const wrapper = mount(Market)
    await flushPromises()

    expect(wrapper.text()).toContain('Kurse nicht verfügbar')
  })

  it('shows "Keine Kurse" when items array is empty', async () => {
    mockMarket([])
    const wrapper = mount(Market)
    await flushPromises()

    expect(wrapper.text()).toContain('Keine Kurse')
  })

  it('renders in small size by default (no provide)', async () => {
    mockMarket([
      makeMarketItem(),
      makeMarketItem({ id: 'MSFT', symbol: 'MSFT', name: 'Microsoft' }),
    ])
    const wrapper = mount(Market)
    await flushPromises()

    expect(wrapper.find('.mkt-list').exists()).toBe(true)
  })

  it('renders in medium size when cellSizes provides value 2', async () => {
    mockMarket([
      makeMarketItem(),
      makeMarketItem({ id: 'MSFT', symbol: 'MSFT', name: 'Microsoft' }),
      makeMarketItem({ id: 'NVDA', symbol: 'NVDA', name: 'Nvidia' }),
      makeMarketItem({ id: 'BTC/USD', symbol: 'BTC/USD', name: 'Bitcoin', asset_type: 'crypto' as const }),
    ])
    const wrapper = mount(Market, {
      global: {
        provide: {
          cellId: 1,
          cellSizes: ref({ 1: 2 }),
        },
      },
    })
    await flushPromises()

    expect(wrapper.find('.mkt-rows').exists()).toBe(true)
  })

  it('renders in large size when cellSizes provides value 4', async () => {
    mockMarket([
      makeMarketItem(),
      makeMarketItem({ id: 'MSFT', symbol: 'MSFT', name: 'Microsoft' }),
    ])
    const wrapper = mount(Market, {
      global: {
        provide: {
          cellId: 2,
          cellSizes: ref({ 2: 4 }),
        },
      },
    })
    await flushPromises()

    expect(wrapper.find('.mkt-large-list').exists()).toBe(true)
  })

  it('clears the refresh interval on unmount', async () => {
    mockMarket()
    const clearSpy = vi.spyOn(window, 'clearInterval')
    const wrapper = mount(Market)
    await flushPromises()
    wrapper.unmount()

    expect(clearSpy).toHaveBeenCalled()
  })

  it('applies mkt-up class for positive change', async () => {
    mockMarket([makeMarketItem({ change: 1.23, percent_change: 0.65 })])
    const wrapper = mount(Market)
    await flushPromises()

    expect(wrapper.find('.mkt-up').exists()).toBe(true)
  })

  it('applies mkt-down class for negative change', async () => {
    mockMarket([makeMarketItem({ change: -2.10, percent_change: -1.05 })])
    const wrapper = mount(Market)
    await flushPromises()

    expect(wrapper.find('.mkt-down').exists()).toBe(true)
  })

  it('renders crypto badge for crypto assets in medium layout', async () => {
    mockMarket([
      makeMarketItem({ id: 'BTC/USD', symbol: 'BTC/USD', name: 'Bitcoin', asset_type: 'crypto' as const }),
      makeMarketItem({ id: 'ETH/USD', symbol: 'ETH/USD', name: 'Ethereum', asset_type: 'crypto' as const }),
    ])
    const wrapper = mount(Market, {
      global: {
        provide: { cellId: 3, cellSizes: ref({ 3: 2 }) },
      },
    })
    await flushPromises()

    expect(wrapper.find('.mkt-badge--crypto').exists()).toBe(true)
  })

  it('renders stock badge for stock assets in medium layout', async () => {
    mockMarket([
      makeMarketItem({ asset_type: 'stock' as const }),
      makeMarketItem({ id: 'MSFT', symbol: 'MSFT', name: 'Microsoft', asset_type: 'stock' as const }),
    ])
    const wrapper = mount(Market, {
      global: {
        provide: { cellId: 4, cellSizes: ref({ 4: 2 }) },
      },
    })
    await flushPromises()

    expect(wrapper.find('.mkt-badge--stock').exists()).toBe(true)
  })
})
