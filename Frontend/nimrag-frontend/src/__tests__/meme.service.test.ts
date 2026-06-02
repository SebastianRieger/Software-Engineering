import { describe, expect, it, vi } from 'vitest'
import { getJson } from '@/services/api'
import { getMemes } from '@/services/meme'

vi.mock('@/services/api', () => ({ getJson: vi.fn() }))

const mockedGetJson = vi.mocked(getJson)

describe('meme service', () => {
  it('requests the meme endpoint', async () => {
    mockedGetJson.mockResolvedValue({ memes: [] })
    await getMemes()
    expect(mockedGetJson).toHaveBeenCalledWith('/meme')
  })
})
