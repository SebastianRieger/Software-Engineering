import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getJson } from '@/services/api'
import { getCurrentWeather, getForecast } from '@/services/weather'

vi.mock('@/services/api', () => ({
  getJson: vi.fn(),
}))

const mockedGetJson = vi.mocked(getJson)

beforeEach(() => {
  mockedGetJson.mockReset()
  mockedGetJson.mockResolvedValue({
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

describe('weather service', () => {
  it('requests the default current weather endpoint', async () => {
    await getCurrentWeather()

    expect(mockedGetJson).toHaveBeenCalledWith('/weather/current')
  })

  it('appends provided query parameters in the backend format', async () => {
    await getCurrentWeather({ lat: 49.0069, lon: 8.4037, city: 'Karlsruhe' })

    expect(mockedGetJson).toHaveBeenCalledWith('/weather/current?lat=49.0069&lon=8.4037&city=Karlsruhe')
  })

  it('requests forecast with default days parameter', async () => {
    await getForecast()

    expect(mockedGetJson).toHaveBeenCalledWith('/weather/forecast?days=5')
  })

  it('requests forecast with custom days and location', async () => {
    await getForecast(3, { lat: 49.0069, lon: 8.4037 })

    expect(mockedGetJson).toHaveBeenCalledWith('/weather/forecast?lat=49.0069&lon=8.4037&days=3')
  })
})