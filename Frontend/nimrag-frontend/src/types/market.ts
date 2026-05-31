export interface MarketItem {
  id: string
  symbol: string
  name: string
  price: number
  change: number
  percent_change: number
  currency: string
  asset_type: 'stock' | 'crypto'
}

export interface MarketResponse {
  items: MarketItem[]
  source: 'live' | 'cache'
}
