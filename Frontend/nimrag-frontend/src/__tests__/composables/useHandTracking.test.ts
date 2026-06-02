import { describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'

const realtime = vi.hoisted(() => ({
  listener: null as ((event: any) => void) | null,
  unsubscribe: vi.fn(),
}))

vi.mock('@/services/realtime', () => ({
  realtimeClient: {
    subscribe: vi.fn((listener: (event: any) => void) => {
      realtime.listener = listener
      return realtime.unsubscribe
    }),
  },
}))

import { useHandTracking } from '@/composables/useHandTracking'

function mountHarness() {
  let exposed: ReturnType<typeof useHandTracking> | null = null
  const Harness = defineComponent({
    setup() {
      exposed = useHandTracking()
      return () => null
    },
  })
  const wrapper = mount(Harness)
  return { wrapper, tracking: exposed! }
}

describe('useHandTracking', () => {
  it('maps index and backend pinch anchor into mirrored cursor space', () => {
    const { tracking } = mountHarness()

    realtime.listener?.({
      eventType: 'HandTrackingUpdated',
      payload: {
        pinch_anchor: [0.25, 0.4],
        pinch_distance: 0.1,
        hands: [
          {
            hand: 'right',
            landmarks: {
              index_tip: [0.2, 0.3],
              thumb_tip: [0.4, 0.5],
            },
          },
        ],
      },
    })

    expect(tracking.indexFingerCursor.value).toEqual({ x: 80, y: 30 })
    expect(tracking.pinchCursor.value).toEqual({ x: 75, y: 40 })
    expect(tracking.backendPinchDistance.value).toBe(0.1)
  })

  it('falls back to the thumb-index midpoint when no backend anchor is present', () => {
    const { tracking } = mountHarness()

    realtime.listener?.({
      eventType: 'HandTrackingUpdated',
      payload: {
        hands: [
          {
            hand: 'right',
            landmarks: {
              index_tip: [0.2, 0.3],
              thumb_tip: [0.4, 0.5],
            },
          },
        ],
      },
    })

    expect(tracking.pinchCursor.value).toEqual({ x: 70, y: 40 })
  })
})
