import { describe, expect, it, vi } from 'vitest'
import { getJson } from '@/services/api'
import { getMarket } from '@/services/market'

vi.mock('@/services/api', () => ({ getJson: vi.fn() }))

const mockedGetJson = vi.mocked(getJson)

describe('market service', () => {
  it('requests the market endpoint with encoded symbols', async () => {
    mockedGetJson.mockResolvedValue({ quotes: [] })
    await getMarket(['AAPL', 'BTC/USD'])
    expect(mockedGetJson).toHaveBeenCalledWith('/market?symbols=AAPL,BTC%2FUSD')
  })
})
