import { getJson } from './api'
import type { AppConfig, AppConfigEnvelope } from '../types/appConfig'

export function getAppConfig(): Promise<AppConfig> {
  return getJson<AppConfigEnvelope>('/config/app').then((response) => response.config)
}