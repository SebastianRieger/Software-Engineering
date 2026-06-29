import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  frameUrl: { value: null, __v_isRef: true } as { value: string | null; __v_isRef: true },
  trackedHands: { value: [], __v_isRef: true } as { value: never[]; __v_isRef: true },
  start: vi.fn(),
  stop: vi.fn(),
}))

vi.mock('@/services/gestureFrameStream', () => ({
  useGestureFrameStream: () => ({
    frameUrl: mocks.frameUrl,
    start: mocks.start,
    stop: mocks.stop,
  }),
}))

vi.mock('@/composables/useHandTracking', () => ({
  useHandTracking: () => ({ trackedHands: mocks.trackedHands }),
}))

import CameraWidget from '@/components/widgets/CameraWidget.vue'

beforeEach(() => {
  mocks.frameUrl.value = null
  mocks.trackedHands.value = []
  mocks.start.mockReset()
  mocks.stop.mockReset()
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ output_dir: '/tmp/capture' }),
  }))
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('CameraWidget', () => {
  it('starts the backend frame stream on mount', async () => {
    mount(CameraWidget)
    await flushPromises()

    expect(mocks.start).toHaveBeenCalledOnce()
  })

  it('renders the backend frame when available', async () => {
    mocks.frameUrl.value = 'data:image/jpeg;base64,abc'
    const wrapper = mount(CameraWidget)
    await flushPromises()

    expect(wrapper.find('img.camera-feed').attributes('src')).toBe(mocks.frameUrl.value)
  })

  it('stops the backend frame stream on unmount', async () => {
    const wrapper = mount(CameraWidget)
    await flushPromises()

    wrapper.unmount()

    expect(mocks.stop).toHaveBeenCalledOnce()
  })
})
