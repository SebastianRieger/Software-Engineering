import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/apiConfig', () => ({
  buildWebSocketUrl: () => 'ws://mirror.example.com/ws',
}))

type MockListener = (event: { data?: string }) => void

class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  static instances: MockWebSocket[] = []

  url: string
  readyState = MockWebSocket.OPEN
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED
  })
  private listeners = new Map<string, Set<MockListener>>()

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  addEventListener(type: string, listener: MockListener): void {
    const listeners = this.listeners.get(type) ?? new Set<MockListener>()
    listeners.add(listener)
    this.listeners.set(type, listeners)
  }

  dispatch(type: string, event: { data?: string } = {}): void {
    this.listeners.get(type)?.forEach((listener) => listener(event))
  }
}

async function loadRealtimeClient() {
  vi.resetModules()
  return import('@/services/realtime')
}

beforeEach(() => {
  MockWebSocket.instances = []
  vi.useFakeTimers()
  vi.stubGlobal('WebSocket', MockWebSocket)
})

afterEach(() => {
  vi.runOnlyPendingTimers()
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.resetModules()
})

describe('realtime service', () => {
  it('opens one socket and forwards parsed events to subscribers', async () => {
    const { realtimeClient } = await loadRealtimeClient()
    const listener = vi.fn()
    const unsubscribe = realtimeClient.subscribe(listener)

    expect(MockWebSocket.instances).toHaveLength(1)
    expect(MockWebSocket.instances[0].url).toBe('ws://mirror.example.com/ws')

    MockWebSocket.instances[0].dispatch('message', {
      data: JSON.stringify({ eventType: 'Pong', payload: { message: 'ok' } }),
    })

    expect(listener).toHaveBeenCalledWith({ eventType: 'Pong', payload: { message: 'ok' } })

    unsubscribe()
  })

  it('ignores malformed websocket payloads', async () => {
    const { realtimeClient } = await loadRealtimeClient()
    const listener = vi.fn()

    realtimeClient.subscribe(listener)
    MockWebSocket.instances[0].dispatch('message', { data: 'not-json' })

    expect(listener).not.toHaveBeenCalled()
  })

  it('reuses the existing socket until the final subscriber unsubscribes', async () => {
    const { realtimeClient } = await loadRealtimeClient()
    const firstListener = vi.fn()
    const secondListener = vi.fn()

    const unsubscribeFirst = realtimeClient.subscribe(firstListener)
    const socket = MockWebSocket.instances[0]
    const unsubscribeSecond = realtimeClient.subscribe(secondListener)

    expect(MockWebSocket.instances).toHaveLength(1)

    unsubscribeFirst()
    expect(socket.close).not.toHaveBeenCalled()

    unsubscribeSecond()
    expect(socket.close).toHaveBeenCalledOnce()
  })

  it('reconnects after the socket closes while listeners remain subscribed', async () => {
    const { realtimeClient } = await loadRealtimeClient()

    realtimeClient.subscribe(vi.fn())

    const socket = MockWebSocket.instances[0]
    socket.readyState = MockWebSocket.CLOSED
    socket.dispatch('close')

    expect(MockWebSocket.instances).toHaveLength(1)

    vi.advanceTimersByTime(1500)

    expect(MockWebSocket.instances).toHaveLength(2)
  })

  it('closes and reconnects after websocket errors while listeners remain subscribed', async () => {
    const { realtimeClient } = await loadRealtimeClient()

    realtimeClient.subscribe(vi.fn())

    const socket = MockWebSocket.instances[0]
    socket.dispatch('error')

    expect(socket.close).toHaveBeenCalledOnce()
    expect(MockWebSocket.instances).toHaveLength(1)

    vi.advanceTimersByTime(1500)

    expect(MockWebSocket.instances).toHaveLength(2)
  })

  it('cancels a scheduled reconnect when the last listener unsubscribes', async () => {
    const clearTimeoutSpy = vi.spyOn(window, 'clearTimeout')
    const { realtimeClient } = await loadRealtimeClient()
    const unsubscribe = realtimeClient.subscribe(vi.fn())

    const socket = MockWebSocket.instances[0]
    socket.readyState = MockWebSocket.CLOSED
    socket.dispatch('close')

    unsubscribe()

    expect(clearTimeoutSpy).toHaveBeenCalled()

    vi.runAllTimers()

    expect(MockWebSocket.instances).toHaveLength(1)
  })
})