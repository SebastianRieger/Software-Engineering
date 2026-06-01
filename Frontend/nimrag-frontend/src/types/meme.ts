export interface MemeItem {
  image_url: string
  title: string
  subreddit: string
  previews: string[]
}

export interface MemeBatchResponse {
  memes: MemeItem[]
  source: 'live' | 'cache'
}
