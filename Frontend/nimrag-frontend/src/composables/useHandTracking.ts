import { ref, onBeforeUnmount } from 'vue'
import { realtimeClient } from '../services/realtime'
import type { RealtimeEvent } from '../types/realtime'

export interface HandLandmarks {
  [name: string]: [number, number]
}

export interface TrackedHand {
  hand: string | null
  landmarks: HandLandmarks
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

  onBeforeUnmount(() => {
    if (hideTimer !== null) clearTimeout(hideTimer)
    unsubscribe()
  })

  return { trackedHands }
}
