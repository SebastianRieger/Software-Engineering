import { getJson } from './api'
import type { DailyFact } from '../types/fact'

export function getFact(): Promise<DailyFact> {
  return getJson<DailyFact>('/fact')
}
