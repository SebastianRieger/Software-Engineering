import { buildApiUrl } from './apiConfig'

export type BackendReachabilityState = 'unknown' | 'reachable' | 'unreachable'

const INITIAL_RETRY_DELAY_MS = 1500
const MAX_RETRY_DELAY_MS = 10000

function isLikelyNetworkError(error: unknown): boolean {
  return error instanceof TypeError
}

class BackendReachabilityService {
  private state: BackendReachabilityState = 'unknown'
  private probeInFlight: Promise<boolean> | null = null
  private nextProbeAt = 0
  private retryDelayMs = INITIAL_RETRY_DELAY_MS

  getState(): BackendReachabilityState {
    return this.state
  }

  getRetryDelayMs(): number {
    if (this.state !== 'unreachable') {
      return INITIAL_RETRY_DELAY_MS
    }

    const remainingMs = this.nextProbeAt - Date.now()
    return remainingMs > 0 ? remainingMs : INITIAL_RETRY_DELAY_MS
  }

  markReachable(): void {
    this.state = 'reachable'
    this.nextProbeAt = 0
    this.retryDelayMs = INITIAL_RETRY_DELAY_MS
  }

  markUnreachable(): void {
    const now = Date.now()
    this.state = 'unreachable'

    if (this.nextProbeAt > now) {
      return
    }

    this.nextProbeAt = now + this.retryDelayMs
    this.retryDelayMs = Math.min(this.retryDelayMs * 2, MAX_RETRY_DELAY_MS)
  }

  noteRequestFailure(error: unknown): void {
    if (isLikelyNetworkError(error)) {
      this.markUnreachable()
    }
  }

  async requestAvailabilityCheck(): Promise<boolean> {
    if (this.state === 'reachable') {
      return true
    }

    if (this.probeInFlight !== null) {
      return this.probeInFlight
    }

    if (this.state === 'unreachable' && Date.now() < this.nextProbeAt) {
      return false
    }

    this.probeInFlight = this.probe()
    return this.probeInFlight
  }

  resetForTests(): void {
    this.state = 'unknown'
    this.probeInFlight = null
    this.nextProbeAt = 0
    this.retryDelayMs = INITIAL_RETRY_DELAY_MS
  }

  private async probe(): Promise<boolean> {
    try {
      const response = await fetch(buildApiUrl('system/status'), {
        headers: { Accept: 'application/json' },
      })

      if (!response.ok) {
        this.markUnreachable()
        return false
      }

      this.markReachable()
      return true
    } catch (error) {
      this.noteRequestFailure(error)
      return false
    } finally {
      this.probeInFlight = null
    }
  }
}

export const backendReachability = new BackendReachabilityService()

export function resetBackendReachabilityForTests(): void {
  backendReachability.resetForTests()
}