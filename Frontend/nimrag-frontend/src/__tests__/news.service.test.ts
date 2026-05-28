import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getJson } from '@/services/api'
import { getNews } from '@/services/news'

vi.mock('@/services/api', () => ({
  getJson: vi.fn(),
}))

const mockedGetJson = vi.mocked(getJson)

beforeEach(() => {
  mockedGetJson.mockReset()
  mockedGetJson.mockResolvedValue({ news: [], source: 'live' })
})

describe('news service', () => {
  it('requests the default backend news endpoint', async () => {
    await getNews()

    expect(mockedGetJson).toHaveBeenCalledWith('/news')
  })

  it('appends configured query parameters in the backend format', async () => {
    await getNews({ ressort: 'sport', regions: [1, 2] })

    expect(mockedGetJson).toHaveBeenCalledWith('/news?ressort=sport&regions=1%2C2')
  })
})