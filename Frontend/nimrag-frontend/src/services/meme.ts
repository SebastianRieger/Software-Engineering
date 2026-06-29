import { getJson } from './api'
import type { MemeBatchResponse } from '../types/meme'

export function getMemes(): Promise<MemeBatchResponse> {
  return getJson<MemeBatchResponse>('/meme')
}
