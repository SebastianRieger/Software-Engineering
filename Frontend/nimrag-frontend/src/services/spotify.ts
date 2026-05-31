import { getJson } from './api'
import type { NowPlayingResponse } from '../types/spotify'

export interface SpotifyAuthStatus {
  authenticated: boolean
  auth_url: string | null
}

export function getNowPlaying(): Promise<NowPlayingResponse> {
  return getJson<NowPlayingResponse>('/spotify/now-playing')
}

export function getAuthStatus(): Promise<SpotifyAuthStatus> {
  return getJson<SpotifyAuthStatus>('/spotify/auth')
}
