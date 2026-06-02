import { getJson } from './api'
import type { BullshitResponse } from '../types/bullshit'

export function getBullshit(): Promise<BullshitResponse> {
  return getJson<BullshitResponse>('/bullshit')
}
