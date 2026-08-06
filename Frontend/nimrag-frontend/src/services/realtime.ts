import { buildWebSocketUrl } from './apiConfig'
import type { RealtimeEvent } from '../types/realtime'

export type RealtimeListener = (event: RealtimeEvent) => void

function logGestureDebugEvent(event: RealtimeEvent): void {
  if (!import.meta.env.DEV) {
    return
  }

  if (event.eventType === 'GestureDetected') {
    const payload = event.payload
    if (payload === null) return
    console.info('[gesture]', payload.gesture, {
      hand: payload.hand ?? null,
      confidence: payload.confidence ?? null,
      activePhase: payload.active_phase ?? null,
      trackingSource: payload.tracking_source ?? null,
      rejectReason: payload.reject_reason ?? null,
    })
    return
  }

  if (event.eventType === 'CommandMatchEvaluated') {
    const payload = event.payload
    if (payload === null || payload.input_source !== 'gesture') return
    console.info('[gesture-match]', `${payload.raw_input} -> ${payload.action ?? 'none'}`, {
      outcome: payload.outcome,
      reason: payload.reason,
    })
    return
  }

  if (event.eventType === 'UIActionRequested') {
    const payload = event.payload
    if (payload === null || payload.input_source !== 'gesture') return
    console.info('[gesture-action]', `${payload.raw_input} -> ${payload.action}`, {
      actionArgs: payload.action_args,
    })
  }
}

class RealtimeClient {
  private socket: WebSocket | null = null
  private listeners = new Set<RealtimeListener>()
  private reconnectTimer: number | null = null

  subscribe(listener: RealtimeListener): () => void {
    this.listeners.add(listener)
    this.ensureConnected()

    return () => {
      this.listeners.delete(listener)
      if (this.listeners.size === 0) {
        this.teardown()
      }
    }
  }

  private ensureConnected(): void {
    if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
      return
    }

    this.socket = new WebSocket(buildWebSocketUrl())
    this.socket.addEventListener('message', (event) => {
      try {
        const payload = JSON.parse(event.data) as RealtimeEvent
        logGestureDebugEvent(payload)
        this.listeners.forEach((listener) => listener(payload))
      } catch {
        // Ignore malformed payloads and keep the connection alive.
      }
    })

    this.socket.addEventListener('close', () => {
      this.socket = null
      if (this.listeners.size > 0 && this.reconnectTimer === null) {
        this.reconnectTimer = window.setTimeout(() => {
          this.reconnectTimer = null
          this.ensureConnected()
        }, 1500)
      }
    })
  }

  private teardown(): void {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  }
}

export const realtimeClient = new RealtimeClient()
