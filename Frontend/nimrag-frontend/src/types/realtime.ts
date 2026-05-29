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
  | PongEvent
  | HandTrackingUpdatedEvent
  | UnknownRealtimeEvent