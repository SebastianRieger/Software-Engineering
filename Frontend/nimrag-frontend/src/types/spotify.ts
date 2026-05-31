export interface SpotifyTrack {
  track_name: string
  artist: string
  album: string
  album_cover_url: string | null
  progress_ms: number
  duration_ms: number
}

export interface NowPlayingResponse {
  is_playing: boolean
  track: SpotifyTrack | null
  queue: SpotifyTrack[]
}
