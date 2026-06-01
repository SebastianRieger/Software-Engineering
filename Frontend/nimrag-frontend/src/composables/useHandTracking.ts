import { ref, computed, onBeforeUnmount } from 'vue'
import { realtimeClient } from '../services/realtime'
import type { RealtimeEvent } from '../types/realtime'

export interface HandLandmarks {
  [name: string]: [number, number]
}

export interface TrackedHand {
  hand: string | null
  landmarks: HandLandmarks
}

export interface CursorPosition {
  x: number
  y: number
}

export function useHandTracking() {
  const trackedHands = ref<TrackedHand[]>([])
  let hideTimer: ReturnType<typeof setTimeout> | null = null

  const unsubscribe = realtimeClient.subscribe((event: RealtimeEvent) => {
    if (event.eventType !== 'HandTrackingUpdated') return
    const payload = (event as { eventType: string; payload: { hands: TrackedHand[] } }).payload
    trackedHands.value = payload?.hands ?? []

    if (hideTimer !== null) clearTimeout(hideTimer)
    if (trackedHands.value.length > 0) {
      hideTimer = setTimeout(() => {
        trackedHands.value = []
      }, 300)
    }
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

  onBeforeUnmount(() => {
    if (hideTimer !== null) clearTimeout(hideTimer)
    unsubscribe()
  })

  return { trackedHands, indexFingerCursor }
}
