import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const handTrackingMock = vi.hoisted(() => ({
  trackedHands: { value: [], __v_isRef: true } as { value: never[]; __v_isRef: true },
}))

vi.mock('@/composables/useHandTracking', () => ({
  useHandTracking: () => handTrackingMock,
}))

import HomeScreen from '@/components/HomeScreen.vue'

class ResizeObserverMock {
  observe(): void {}
  disconnect(): void {}
}

describe('HomeScreen', () => {
  beforeEach(() => {
    vi.stubGlobal('ResizeObserver', ResizeObserverMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the error state ahead of the loader when no frame is available', () => {
    const wrapper = mount(HomeScreen, {
      props: {
        cameras: [],
        currentIndex: 0,
        frameUrl: null,
        error: 'Kamera konnte nicht geladen werden.',
        loading: true,
        state: 'error',
        slideDirection: null,
      },
    })

    expect(wrapper.find('.camera-state--error').exists()).toBe(true)
    expect(wrapper.text()).toContain('Kamera konnte nicht geladen werden.')
    expect(wrapper.find('.camera-state-inner').exists()).toBe(false)
  })
})
