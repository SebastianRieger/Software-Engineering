import { describe, expect, it, vi } from 'vitest'
import { getJson } from '@/services/api'
import { getTrivia } from '@/services/trivia'

vi.mock('@/services/api', () => ({ getJson: vi.fn() }))

const mockedGetJson = vi.mocked(getJson)

describe('trivia service', () => {
  it('requests the trivia endpoint', async () => {
    mockedGetJson.mockResolvedValue({ question: 'What is 2+2?', answer: '4' })
    await getTrivia()
    expect(mockedGetJson).toHaveBeenCalledWith('/trivia')
  })
})
