import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/appConfig', () => ({ getAppConfig: vi.fn() }))

import { getAppConfig } from '@/services/appConfig'
import { loadAppConfig, resetAppConfigCache, DEFAULT_APP_CONFIG } from '@/composables/useAppConfig'

const mockedGetAppConfig = vi.mocked(getAppConfig)

beforeEach(() => {
  resetAppConfigCache()
  mockedGetAppConfig.mockReset()
})

describe('useAppConfig', () => {
  it('loadAppConfig() fetches and returns config', async () => {
    mockedGetAppConfig.mockResolvedValue(DEFAULT_APP_CONFIG)
    const config = await loadAppConfig()
    expect(mockedGetAppConfig).toHaveBeenCalledOnce()
    expect(config).toEqual(DEFAULT_APP_CONFIG)
  })

  it('loadAppConfig() caches the result on repeated calls', async () => {
    mockedGetAppConfig.mockResolvedValue(DEFAULT_APP_CONFIG)
    await loadAppConfig()
    await loadAppConfig()
    expect(mockedGetAppConfig).toHaveBeenCalledOnce()
  })

  it('loadAppConfig() falls back to DEFAULT_APP_CONFIG on error', async () => {
    mockedGetAppConfig.mockRejectedValue(new Error('offline'))
    const config = await loadAppConfig()
    expect(config).toEqual(DEFAULT_APP_CONFIG)
  })

  it('resetAppConfigCache() clears the cache', async () => {
    mockedGetAppConfig.mockResolvedValue(DEFAULT_APP_CONFIG)
    await loadAppConfig()
    resetAppConfigCache()
    await loadAppConfig()
    expect(mockedGetAppConfig).toHaveBeenCalledTimes(2)
  })
})
