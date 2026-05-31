import { getJson } from './api'
import type { MarketResponse } from '../types/market'

export function getMarket(symbols: string[]): Promise<MarketResponse> {
  const encodedSymbols = symbols.map(s => encodeURIComponent(s)).join(',')
  return getJson<MarketResponse>(`/market?symbols=${encodedSymbols}`)
}
