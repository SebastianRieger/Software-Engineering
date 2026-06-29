import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getJson } from '@/services/api'
import { checkExternalApiHealth } from '@/services/systemHealth'

vi.mock('@/services/api', () => ({
  getJson: vi.fn(),
}))

const mockedGetJson = vi.mocked(getJson)

beforeEach(() => {
  mockedGetJson.mockReset()
  mockedGetJson.mockResolvedValue({ checked_at: new Date().toISOString(), providers: [] })
})

describe('system health service', () => {
  it('requests the external API startup health endpoint', async () => {
    await checkExternalApiHealth()

    expect(mockedGetJson).toHaveBeenCalledWith('/system/external-apis/health')
  })
})