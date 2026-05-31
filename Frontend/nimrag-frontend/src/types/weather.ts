export interface Coordinates {
  lat: number
  lon: number
}

export interface WeatherCurrentResponse {
  location_name: string | null
  coordinates: Coordinates
  temperature: number
  humidity: number
  condition: string
  wind_speed: number
  timestamp: string
  source: 'live' | 'cache'
}

export interface WeatherForecastEntry {
  date: string
  min_temp: number
  max_temp: number
  condition: string
}

export interface WeatherForecastResponse {
  location_name: string | null
  coordinates: Coordinates
  days: number
  generated_at: string
  forecast: WeatherForecastEntry[]
  source: 'live' | 'cache'
}