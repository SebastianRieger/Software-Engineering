import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import WeatherWidget from '@/components/widgets/WeatherWidget.vue'
import { loadAppConfig } from '@/composables/useAppConfig'
import { getCurrentWeather } from '@/services/weather'

vi.mock('@/composables/useAppConfig', () => ({
  loadAppConfig: vi.fn(),
}))

vi.mock('@/services/weather', () => ({
  getCurrentWeather: vi.fn(),
}))

const mockedLoadAppConfig = vi.mocked(loadAppConfig)
const mockedGetCurrentWeather = vi.mocked(getCurrentWeather)

beforeEach(() => {
  mockedLoadAppConfig.mockReset()
  mockedGetCurrentWeather.mockReset()
  mockedLoadAppConfig.mockResolvedValue({
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
    },
  })
  mockedGetCurrentWeather.mockResolvedValue({
    location_name: 'Karlsruhe',
    coordinates: { lat: 49.0069, lon: 8.4037 },
    temperature: 21.4,
    humidity: 63,
    condition: 'Wolkig',
    wind_speed: 3.1,
    timestamp: new Date().toISOString(),
    source: 'live',
  })
})

describe('WeatherWidget', () => {
  it('renders without errors', async () => {
    const wrapper = mount(WeatherWidget)
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('displays the "Wetter" heading', async () => {
    const wrapper = mount(WeatherWidget)
    await flushPromises()
    expect(wrapper.find('h3').text()).toBe('Wetter')
  })

  it('loads and shows the city name from the backend service', async () => {
    const wrapper = mount(WeatherWidget)
    await flushPromises()

    expect(mockedGetCurrentWeather).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('Karlsruhe')
  })

  it('shows the rounded temperature', async () => {
    const wrapper = mount(WeatherWidget)
    await flushPromises()

    expect(wrapper.text()).toContain('21°C')
  })

  it('shows the condition', async () => {
    const wrapper = mount(WeatherWidget)
    await flushPromises()

    expect(wrapper.text()).toContain('Wolkig')
  })

  it('shows an error when loading weather data fails', async () => {
    mockedGetCurrentWeather.mockRejectedValueOnce(new Error('Backend nicht erreichbar'))

    const wrapper = mount(WeatherWidget)
    await flushPromises()

    expect(wrapper.text()).toContain('Backend nicht erreichbar')
  })
})
