import type { CalibrationRealtimeEvent } from './calibration'
import type { LEDStateResponse } from './hardware'
import type {
  CommandMatchEvaluatedPayload,
  GestureDetectedPayload,
  RawInputDetectedPayload,
  UIActionRequestedPayload,
} from './interactions'

export interface GestureDetectedEvent {
  eventType: 'GestureDetected'
  payload: GestureDetectedPayload
}

export interface RawInputDetectedEvent {
  eventType: 'RawInputDetected'
  payload: RawInputDetectedPayload
}

export interface UIActionRequestedEvent {
  eventType: 'UIActionRequested'
  payload: UIActionRequestedPayload
}

export interface CommandMatchEvaluatedEvent {
  eventType: 'CommandMatchEvaluated'
  payload: CommandMatchEvaluatedPayload
}

export interface VoiceCommandDetectedPayload {
  command: string
  raw_input: string
  timestamp: string
  source: 'microphone'
  transcript: string | null
  partial: boolean
  device_index: number | null
}

export interface VoiceCommandDetectedEvent {
  eventType: 'VoiceCommandDetected'
  payload: VoiceCommandDetectedPayload
}

export interface LEDStateChangedEvent {
  eventType: 'LEDStateChanged'
  payload: LEDStateResponse
}

export interface PongEvent {
  eventType: 'Pong'
  payload: { message: string }
}

export type RealtimeEvent =
  | CalibrationRealtimeEvent
  | GestureDetectedEvent
  | RawInputDetectedEvent
  | CommandMatchEvaluatedEvent
  | UIActionRequestedEvent
  | VoiceCommandDetectedEvent
  | LEDStateChangedEvent
  | PongEvent