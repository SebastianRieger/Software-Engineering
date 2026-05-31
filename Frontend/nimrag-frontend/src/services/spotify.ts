import { getJson } from './api'
import type { NowPlayingResponse } from '../types/spotify'

export function getNowPlaying(): Promise<NowPlayingResponse> {
  return getJson<NowPlayingResponse>('/spotify/now-playing')
}
