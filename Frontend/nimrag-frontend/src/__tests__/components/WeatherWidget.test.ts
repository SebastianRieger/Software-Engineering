import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import WeatherWidget from '@/components/widgets/WeatherWidget.vue'
import { getCurrentWeather } from '@/services/weather'

vi.mock('@/services/weather', () => ({
  getCurrentWeather: vi.fn(),
}))

const mockedGetCurrentWeather = vi.mocked(getCurrentWeather)

beforeEach(() => {
  mockedGetCurrentWeather.mockReset()
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
