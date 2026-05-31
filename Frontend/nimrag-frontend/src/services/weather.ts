import { getJson } from './api'
import type { WeatherCurrentResponse, WeatherForecastResponse } from '../types/weather'

export interface WeatherQuery {
  lat?: number
  lon?: number
  city?: string
}

function buildWeatherParams(query: WeatherQuery): URLSearchParams {
  const p = new URLSearchParams()
  if (query.lat !== undefined) p.set('lat', String(query.lat))
  if (query.lon !== undefined) p.set('lon', String(query.lon))
  if (query.city) p.set('city', query.city)
  return p
}

export function getCurrentWeather(query: WeatherQuery = {}): Promise<WeatherCurrentResponse> {
  const qs = buildWeatherParams(query).toString()
  return getJson<WeatherCurrentResponse>(qs ? `/weather/current?${qs}` : '/weather/current')
}

export function getForecast(days = 5, query: WeatherQuery = {}): Promise<WeatherForecastResponse> {
  const p = buildWeatherParams(query)
  p.set('days', String(days))
  return getJson<WeatherForecastResponse>(`/weather/forecast?${p.toString()}`)
}