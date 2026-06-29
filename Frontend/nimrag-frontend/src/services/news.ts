import { getJson } from './api'
import type { NewsQuery, NewsResponse } from '../types/news'

function buildNewsPath(query: NewsQuery = {}): string {
  const searchParams = new URLSearchParams()

  if (query.ressort) {
    searchParams.set('ressort', query.ressort)
  }
  if (query.regions?.length) {
    searchParams.set('regions', query.regions.join(','))
  }

  const queryString = searchParams.toString()
  return queryString.length > 0 ? `/news?${queryString}` : '/news'
}

export function getNews(query: NewsQuery = {}): Promise<NewsResponse> {
  return getJson<NewsResponse>(buildNewsPath(query))
}