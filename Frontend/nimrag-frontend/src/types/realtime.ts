import type {
  CommandMatchEvaluatedPayload,
  RawInputDetectedPayload,
  UIActionRequestedPayload,
} from './interactions'

export interface UIActionRequestedEvent {
  eventType: 'UIActionRequested'
  payload: UIActionRequestedPayload
}

export interface CommandMatchEvaluatedEvent {
  eventType: 'CommandMatchEvaluated'
  payload: CommandMatchEvaluatedPayload
}

export interface RawInputDetectedEvent {
  eventType: 'RawInputDetected'
  payload: RawInputDetectedPayload
}

export interface GestureDetectedEvent {
  eventType: 'GestureDetected'
  payload: {
    gesture: string
    timestamp: string
    source: 'camera'
    hand: string | null
    confidence: number | null
    tracking_source: string | null
    tracking_quality: number | null
    active_phase: 'idle' | 'preparing' | 'holding' | 'committing' | 'releasing' | 'cooldown' | null
    candidate_scores: Record<string, number>
    reject_reason: string | null
    spec_id: string | null
    dominant_hand_pose: string | null
    primitive_hits: Record<string, number>
  }
}

export interface PongEvent {
  eventType: 'Pong'
  payload: {
    message: string
  }
}

export interface HandTrackingUpdatedEvent {
  eventType: 'HandTrackingUpdated'
  payload: {
    hands: Array<{
      hand: string | null
      landmarks: Record<string, [number, number]>
    }>
  }
}

export interface UnknownRealtimeEvent {
  eventType: string
  payload: Record<string, unknown> | null
}

export type RealtimeEvent =
  | UIActionRequestedEvent
  | CommandMatchEvaluatedEvent
  | RawInputDetectedEvent
  | GestureDetectedEvent
  | PongEvent
  | HandTrackingUpdatedEvent
  | UnknownRealtimeEvent