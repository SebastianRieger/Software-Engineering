import { getJson } from './api'
import type { WeatherCurrentResponse } from '../types/weather'

export interface WeatherQuery {
  lat?: number
  lon?: number
  city?: string
}

function buildCurrentWeatherPath(query: WeatherQuery = {}): string {
  const searchParams = new URLSearchParams()

  if (query.lat !== undefined) {
    searchParams.set('lat', String(query.lat))
  }
  if (query.lon !== undefined) {
    searchParams.set('lon', String(query.lon))
  }
  if (query.city) {
    searchParams.set('city', query.city)
  }

  const queryString = searchParams.toString()
  return queryString.length > 0 ? `/weather/current?${queryString}` : '/weather/current'
}

export function getCurrentWeather(query: WeatherQuery = {}): Promise<WeatherCurrentResponse> {
  return getJson<WeatherCurrentResponse>(buildCurrentWeatherPath(query))
}