export interface ExternalApiHealthProvider {
  provider: string
  status: 'ok' | 'down'
  checked_at: string
  response_time_ms: number
  error?: string | null
}

export interface ExternalApiHealthResponse {
  checked_at: string
  providers: ExternalApiHealthProvider[]
}