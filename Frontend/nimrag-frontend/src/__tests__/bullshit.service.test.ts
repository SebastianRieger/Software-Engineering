import { describe, expect, it, vi } from 'vitest'
import { getJson } from '@/services/api'
import { getBullshit } from '@/services/bullshit'

vi.mock('@/services/api', () => ({ getJson: vi.fn() }))

const mockedGetJson = vi.mocked(getJson)

describe('bullshit service', () => {
  it('requests the bullshit endpoint', async () => {
    mockedGetJson.mockResolvedValue({ phrase: 'Synergize the deliverables' })
    await getBullshit()
    expect(mockedGetJson).toHaveBeenCalledWith('/bullshit')
  })
})
