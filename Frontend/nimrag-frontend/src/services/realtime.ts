import { buildWebSocketUrl } from './apiConfig'
import { backendReachability } from './backendReachability'
import type { RealtimeEvent } from '../types/realtime'

export type RealtimeListener = (event: RealtimeEvent) => void

const INITIAL_RECONNECT_DELAY_MS = 1500
const MAX_RECONNECT_DELAY_MS = 10000

class RealtimeClient {
  private socket: WebSocket | null = null
  private listeners = new Set<RealtimeListener>()
  private reconnectTimer: number | null = null
  private reconnectDelayMs = INITIAL_RECONNECT_DELAY_MS
  private connectInFlight = false

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

  resetForTests(): void {
    this.listeners.clear()
    this.teardown()
    backendReachability.resetForTests()
  }

  private ensureConnected(): void {
    if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
      return
    }

    if (this.connectInFlight) {
      return
    }

    this.connectInFlight = true
    void this.openSocketWhenAvailable()
  }

  private async openSocketWhenAvailable(): Promise<void> {
    const reachable = await backendReachability.requestAvailabilityCheck()
    this.connectInFlight = false

    if (this.listeners.size === 0) {
      return
    }

    if (!reachable) {
      this.scheduleReconnect(Math.max(this.reconnectDelayMs, backendReachability.getRetryDelayMs()))
      return
    }

    if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
      return
    }

    this.socket = new WebSocket(buildWebSocketUrl())
    this.socket.addEventListener('open', () => {
      backendReachability.markReachable()
      this.reconnectDelayMs = INITIAL_RECONNECT_DELAY_MS
    })
    this.socket.addEventListener('message', (event) => {
      try {
        const payload = JSON.parse(event.data) as RealtimeEvent
        this.listeners.forEach((listener) => listener(payload))
      } catch {
        // Ignore malformed payloads and keep the connection alive.
      }
    })

    this.socket.addEventListener('close', () => {
      this.socket = null
      backendReachability.markUnreachable()
      this.scheduleReconnect(Math.max(this.reconnectDelayMs, backendReachability.getRetryDelayMs()))
    })
  }

  private scheduleReconnect(delayMs = this.reconnectDelayMs): void {
    if (this.listeners.size === 0 || this.reconnectTimer !== null) {
      return
    }

    const effectiveDelayMs = Math.min(delayMs, MAX_RECONNECT_DELAY_MS)
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      this.ensureConnected()
    }, effectiveDelayMs)
    this.reconnectDelayMs = Math.min(effectiveDelayMs * 2, MAX_RECONNECT_DELAY_MS)
  }

  private teardown(): void {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    this.reconnectDelayMs = INITIAL_RECONNECT_DELAY_MS
    this.connectInFlight = false

    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  }
}

export const realtimeClient = new RealtimeClient()

export function resetRealtimeClientForTests(): void {
  realtimeClient.resetForTests()
}