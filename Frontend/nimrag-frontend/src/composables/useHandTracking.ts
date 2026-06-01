import { ref, computed, onBeforeUnmount } from 'vue'
import { realtimeClient } from '../services/realtime'
import type { RealtimeEvent } from '../types/realtime'

const HAND_LOST_GRACE_MS = 650

export interface HandLandmarks {
  [name: string]: [number, number]
}

export interface TrackedHand {
  hand: string | null
  landmarks: HandLandmarks
  pinch_anchor?: [number, number] | null
  pinch_distance?: number | null
}

export interface CursorPosition {
  x: number
  y: number
}

export function useHandTracking() {
  const trackedHands = ref<TrackedHand[]>([])
  const backendPinchAnchor = ref<[number, number] | null>(null)
  const backendPinchDistance = ref<number | null>(null)
  const isHandTrackingActive = ref(false)
  let hideTimer: ReturnType<typeof setTimeout> | null = null

  const clearLostHandTimer = (): void => {
    if (hideTimer !== null) {
      clearTimeout(hideTimer)
      hideTimer = null
    }
  }

  const clearTrackingState = (): void => {
    trackedHands.value = []
    backendPinchAnchor.value = null
    backendPinchDistance.value = null
    isHandTrackingActive.value = false
    hideTimer = null
  }

  const unsubscribe = realtimeClient.subscribe((event: RealtimeEvent) => {
    if (event.eventType !== 'HandTrackingUpdated') return
    const payload = (event as {
      eventType: string
      payload: {
        hands: TrackedHand[]
        pinch_anchor?: [number, number] | null
        pinch_distance?: number | null
      }
    }).payload
    const hands = payload?.hands ?? []
    if (hands.length === 0) {
      if (isHandTrackingActive.value && hideTimer === null) {
        hideTimer = setTimeout(clearTrackingState, HAND_LOST_GRACE_MS)
      }
      return
    }

    clearLostHandTimer()
    trackedHands.value = hands
    backendPinchAnchor.value = payload?.pinch_anchor ?? hands[0]?.pinch_anchor ?? null
    backendPinchDistance.value = payload?.pinch_distance ?? hands[0]?.pinch_distance ?? null
    isHandTrackingActive.value = true
  })

  // Index finger tip position in viewport-percentage space (0-100).
  // X is mirrored (1 - raw_x) to match the mirrored camera feed.
  const indexFingerCursor = computed<CursorPosition | null>(() => {
    const hand = trackedHands.value[0]
    if (!hand) return null
    const tip = hand.landmarks['index_tip']
    if (!tip) return null
    return { x: (1 - tip[0]) * 100, y: tip[1] * 100 }
  })

  const pinchCursor = computed<CursorPosition | null>(() => {
    if (backendPinchAnchor.value) {
      const [x, y] = backendPinchAnchor.value
      return { x: (1 - x) * 100, y: y * 100 }
    }

    const hand = trackedHands.value[0]
    if (!hand) return null
    const thumb = hand.landmarks['thumb_tip']
    const index = hand.landmarks['index_tip']
    if (!thumb || !index) return indexFingerCursor.value
    const x = (thumb[0] + index[0]) / 2
    const y = (thumb[1] + index[1]) / 2
    return { x: (1 - x) * 100, y: y * 100 }
  })

  onBeforeUnmount(() => {
    clearLostHandTimer()
    unsubscribe()
  })

  return {
    trackedHands,
    indexFingerCursor,
    pinchCursor,
    backendPinchDistance,
    isHandTrackingActive,
  }
}
