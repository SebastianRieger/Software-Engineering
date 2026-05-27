import { getJson } from './api'
import type { ExternalApiHealthResponse } from '../types/systemHealth'

export function checkExternalApiHealth(): Promise<ExternalApiHealthResponse> {
  return getJson<ExternalApiHealthResponse>('/system/external-apis/health')
}