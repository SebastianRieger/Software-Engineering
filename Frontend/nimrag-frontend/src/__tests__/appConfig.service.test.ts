import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getJson } from '@/services/api'
import { getAppConfig } from '@/services/appConfig'

vi.mock('@/services/api', () => ({
  getJson: vi.fn(),
}))

const mockedGetJson = vi.mocked(getJson)

beforeEach(() => {
  mockedGetJson.mockReset()
  mockedGetJson.mockResolvedValue({
    config: {
      version: 1,
      system: {
        location_name: 'Karlsruhe',
        latitude: 49.0069,
        longitude: 8.4037,
        units: 'metric',
        theme: 'dark',
        weather_refresh_seconds: 900,
      },
      widgets: {
        weather: { refresh_seconds: 900 },
        news: { ressort: 'wissen', regions: [4], refresh_seconds: 1800 },
        camera: { preferred_device_id: null, preferred_device_label: null },
      },
    },
  })
})

describe('app config service', () => {
  it('requests the backend app config endpoint', async () => {
    const config = await getAppConfig()

    expect(mockedGetJson).toHaveBeenCalledWith('/config/app')
    expect(config.system.location_name).toBe('Karlsruhe')
  })
})