import { computed, ref } from 'vue'

import type { UIActionRequestedPayload } from '../types/interactions'
import type {
  CommandMatchEvaluatedEvent,
  GestureDetectedEvent,
  HandTrackingUpdatedEvent,
  RawInputDetectedEvent,
  RealtimeEvent,
  UIActionRequestedEvent,
} from '../types/realtime'

export type GestureDebugTone = 'neutral' | 'ok' | 'warn' | 'error'

export interface GestureDebugEntry {
  id: number
  at: string
  type: string
  summary: string
  detail: string
  tone: GestureDebugTone
}

const MAX_ENTRIES = 12

function formatClock(value: string | null | undefined): string {
  if (!value) return new Date().toLocaleTimeString()
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return new Date().toLocaleTimeString()
  return parsed.toLocaleTimeString()
}

function countLandmarks(event: RealtimeEvent): number {
  if (event.eventType !== 'HandTrackingUpdated') return 0
  const payload = (event as HandTrackingUpdatedEvent).payload
  return payload.hands.reduce((total, hand) => total + Object.keys(hand.landmarks).length, 0)
}

function formatMetadata(metadata: Record<string, unknown> | undefined): string {
  if (!metadata || Object.keys(metadata).length === 0) return ''
  return Object.entries(metadata)
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(', ')
}

export function useGestureDebug() {
  const entries = ref<GestureDebugEntry[]>([])
  const lastTrackingAt = ref<string | null>(null)
  const trackedHandCount = ref(0)
  const trackedLandmarkCount = ref(0)
  const lastGesture = ref('none')
  const lastGestureDetail = ref('No gesture event yet')
  const lastCommand = ref('none')
  const lastCommandDetail = ref('No command mapping yet')
  const lastAction = ref('none')
  const lastActionDetail = ref('No UI action yet')
  const lastDispatch = ref('none')
  const lastDispatchDetail = ref('No frontend dispatch yet')

  let nextId = 1

  function pushEntry(entry: Omit<GestureDebugEntry, 'id'>): void {
    entries.value = [{ id: nextId++, ...entry }, ...entries.value].slice(0, MAX_ENTRIES)
  }

  function recordRealtimeEvent(event: RealtimeEvent): void {
    switch (event.eventType) {
      case 'HandTrackingUpdated': {
        const payload = (event as HandTrackingUpdatedEvent).payload
        const timestamp = new Date().toISOString()
        const landmarks = countLandmarks(event)
        trackedHandCount.value = payload.hands.length
        trackedLandmarkCount.value = landmarks
        lastTrackingAt.value = timestamp
        pushEntry({
          at: formatClock(timestamp),
          type: 'tracking',
          summary: `${payload.hands.length} hand(s)`,
          detail: `${landmarks} landmark points`,
          tone: payload.hands.length > 0 ? 'ok' : 'warn',
        })
        return
      }

      case 'GestureDetected': {
        const payload = (event as GestureDetectedEvent).payload
        lastGesture.value = payload.gesture
        lastGestureDetail.value = [
          payload.confidence != null ? `confidence ${payload.confidence.toFixed(2)}` : null,
          payload.active_phase ? `phase ${payload.active_phase}` : null,
          payload.reject_reason ? `reject ${payload.reject_reason}` : null,
        ].filter(Boolean).join(' | ') || 'detected'
        pushEntry({
          at: formatClock(payload.timestamp),
          type: 'gesture',
          summary: payload.gesture,
          detail: lastGestureDetail.value,
          tone: payload.reject_reason ? 'warn' : 'ok',
        })
        return
      }

      case 'RawInputDetected': {
        const payload = (event as RawInputDetectedEvent).payload
        pushEntry({
          at: formatClock(payload.timestamp),
          type: 'raw',
          summary: `${payload.input_source}: ${payload.raw_input}`,
          detail: formatMetadata(payload.metadata) || 'raw input emitted',
          tone: 'neutral',
        })
        return
      }

      case 'CommandMatchEvaluated': {
        const payload = (event as CommandMatchEvaluatedEvent).payload
        lastCommand.value = payload.action ?? payload.raw_input
        lastCommandDetail.value = `${payload.outcome}${payload.reason ? ` (${payload.reason})` : ''}`
        pushEntry({
          at: formatClock(payload.timestamp),
          type: 'command',
          summary: payload.action ?? payload.raw_input,
          detail: lastCommandDetail.value,
          tone: payload.outcome === 'accepted' ? 'ok' : payload.outcome === 'suppressed' ? 'warn' : 'error',
        })
        return
      }

      case 'UIActionRequested': {
        const payload = (event as UIActionRequestedEvent).payload
        lastAction.value = payload.action
        lastActionDetail.value = `${payload.input_source}: ${payload.raw_input}`
        pushEntry({
          at: formatClock(payload.timestamp),
          type: 'action',
          summary: payload.action,
          detail: lastActionDetail.value,
          tone: 'ok',
        })
        return
      }
    }
  }

  function recordDispatchResult(payload: UIActionRequestedPayload, handled: boolean): void {
    lastDispatch.value = handled ? 'handled' : 'blocked'
    lastDispatchDetail.value = `${payload.action} from ${payload.raw_input}`
    pushEntry({
      at: formatClock(payload.timestamp),
      type: 'frontend',
      summary: handled ? 'handled' : 'blocked',
      detail: lastDispatchDetail.value,
      tone: handled ? 'ok' : 'warn',
    })
  }

  const trackingStatus = computed(() => {
    if (lastTrackingAt.value === null) return 'No tracking events'
    return `${trackedHandCount.value} hand(s), ${trackedLandmarkCount.value} points`
  })

  return {
    entries,
    trackingStatus,
    lastGesture,
    lastGestureDetail,
    lastCommand,
    lastCommandDetail,
    lastAction,
    lastActionDetail,
    lastDispatch,
    lastDispatchDetail,
    recordRealtimeEvent,
    recordDispatchResult,
  }
}
