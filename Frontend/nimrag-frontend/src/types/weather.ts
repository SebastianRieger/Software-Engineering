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