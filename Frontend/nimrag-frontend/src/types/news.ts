import type { NewsRessort } from './appConfig'

export interface NewsTeaserImage {
  imageVariants?: Record<string, string> | null
  alttext?: string | null
}

export interface NewsItem {
  sophoraId: string
  title: string
  topline?: string | null
  firstSentence?: string | null
  date?: string | null
  shareURL?: string | null
  detailsweb?: string | null
  ressort?: string | null
  breakingNews?: boolean | null
  teaserImage?: NewsTeaserImage | null
}

export interface NewsQuery {
  ressort?: NewsRessort | null
  regions?: number[]
}

export interface NewsResponse {
  news: NewsItem[]
  source: 'live' | 'cache'
}