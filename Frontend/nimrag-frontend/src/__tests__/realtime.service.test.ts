import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

type MockListener = (event: { data?: string }) => void

const reachabilityMock = {
  requestAvailabilityCheck: vi.fn<() => Promise<boolean>>(),
  getRetryDelayMs: vi.fn<() => number>(),
  markReachable: vi.fn(),
  markUnreachable: vi.fn(),
  resetForTests: vi.fn(),
}

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
  vi.doMock('@/services/apiConfig', () => ({
    buildWebSocketUrl: () => 'ws://mirror.example.com/ws',
  }))
  vi.doMock('@/services/backendReachability', () => ({
    backendReachability: reachabilityMock,
  }))
  return import('@/services/realtime')
}

beforeEach(() => {
  MockWebSocket.instances = []
  vi.useFakeTimers()
  reachabilityMock.requestAvailabilityCheck.mockReset()
  reachabilityMock.requestAvailabilityCheck.mockResolvedValue(true)
  reachabilityMock.getRetryDelayMs.mockReset()
  reachabilityMock.getRetryDelayMs.mockReturnValue(1500)
  reachabilityMock.markReachable.mockReset()
  reachabilityMock.markUnreachable.mockReset()
  reachabilityMock.resetForTests.mockReset()
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

    await Promise.resolve()

    expect(MockWebSocket.instances).toHaveLength(1)
    expect(MockWebSocket.instances[0].url).toBe('ws://mirror.example.com/ws')
    expect(reachabilityMock.requestAvailabilityCheck).toHaveBeenCalledOnce()

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
    await Promise.resolve()
    MockWebSocket.instances[0].dispatch('message', { data: 'not-json' })

    expect(listener).not.toHaveBeenCalled()
  })

  it('reuses the existing socket until the final subscriber unsubscribes', async () => {
    const { realtimeClient } = await loadRealtimeClient()
    const firstListener = vi.fn()
    const secondListener = vi.fn()

    const unsubscribeFirst = realtimeClient.subscribe(firstListener)
    await Promise.resolve()
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
    await Promise.resolve()

    const socket = MockWebSocket.instances[0]
    socket.readyState = MockWebSocket.CLOSED
    socket.dispatch('close')

    expect(MockWebSocket.instances).toHaveLength(1)

    vi.advanceTimersByTime(1500)
    await Promise.resolve()

    expect(MockWebSocket.instances).toHaveLength(2)
  })

  it('backs off websocket reconnect attempts after repeated close events', async () => {
    const { realtimeClient } = await loadRealtimeClient()

    realtimeClient.subscribe(vi.fn())
    await Promise.resolve()

    const firstSocket = MockWebSocket.instances[0]
    firstSocket.readyState = MockWebSocket.CLOSED
    firstSocket.dispatch('close')

    vi.advanceTimersByTime(1499)
    expect(MockWebSocket.instances).toHaveLength(1)

    vi.advanceTimersByTime(1)
    await Promise.resolve()
    expect(MockWebSocket.instances).toHaveLength(2)

    const secondSocket = MockWebSocket.instances[1]
    secondSocket.readyState = MockWebSocket.CLOSED
    secondSocket.dispatch('close')

    vi.advanceTimersByTime(2999)
    expect(MockWebSocket.instances).toHaveLength(2)

    vi.advanceTimersByTime(1)
    await Promise.resolve()
    expect(MockWebSocket.instances).toHaveLength(3)
  })

  it('skips websocket creation while shared backend cooldown is active', async () => {
    const { realtimeClient } = await loadRealtimeClient()
    reachabilityMock.requestAvailabilityCheck.mockResolvedValue(false)

    realtimeClient.subscribe(vi.fn())
    await Promise.resolve()

    expect(MockWebSocket.instances).toHaveLength(0)
    expect(reachabilityMock.requestAvailabilityCheck).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(1499)
    await Promise.resolve()

    expect(MockWebSocket.instances).toHaveLength(0)
    expect(reachabilityMock.requestAvailabilityCheck).toHaveBeenCalledTimes(1)
  })

  it('cancels a scheduled reconnect when the last listener unsubscribes', async () => {
    const { realtimeClient } = await loadRealtimeClient()
    const clearTimeoutSpy = vi.spyOn(window, 'clearTimeout')
    const unsubscribe = realtimeClient.subscribe(vi.fn())
    await Promise.resolve()

    const socket = MockWebSocket.instances[0]
    socket.readyState = MockWebSocket.CLOSED
    socket.dispatch('close')

    unsubscribe()

    expect(clearTimeoutSpy).toHaveBeenCalled()

    vi.runAllTimers()

    expect(MockWebSocket.instances).toHaveLength(1)
  })
})