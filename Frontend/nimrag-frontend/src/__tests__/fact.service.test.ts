import { describe, expect, it, vi } from 'vitest'
import { getJson } from '@/services/api'
import { getFact } from '@/services/fact'

vi.mock('@/services/api', () => ({ getJson: vi.fn() }))

const mockedGetJson = vi.mocked(getJson)

describe('fact service', () => {
  it('requests the fact endpoint', async () => {
    mockedGetJson.mockResolvedValue({ fact: 'Honey never spoils.' })
    await getFact()
    expect(mockedGetJson).toHaveBeenCalledWith('/fact')
  })
})
