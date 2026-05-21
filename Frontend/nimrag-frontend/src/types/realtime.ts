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

export interface UnknownRealtimeEvent {
  eventType: string
  payload: Record<string, unknown> | null
}

export type RealtimeEvent =
  | UIActionRequestedEvent
  | CommandMatchEvaluatedEvent
  | RawInputDetectedEvent
  | PongEvent
  | UnknownRealtimeEvent