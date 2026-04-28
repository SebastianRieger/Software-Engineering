import { API_BASE_URL } from './apiConfig'
import type { RealtimeEvent } from '../types/hardware'

type RealtimeListener = (event: RealtimeEvent) => void

function buildWebSocketUrl(): string {
  const origin = API_BASE_URL.replace(/\/api\/v1$/, '')
  if (origin.startsWith('https://')) {
    return `${origin.replace('https://', 'wss://')}/ws`
  }
  return `${origin.replace('http://', 'ws://')}/ws`
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