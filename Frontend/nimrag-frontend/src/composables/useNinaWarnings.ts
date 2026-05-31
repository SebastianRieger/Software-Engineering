import { readonly, ref } from 'vue'

export interface NinaNormalizedWarning {
  id: string
  severity: string
  headline: string
  sender_name: string
  event: string | null
  sent: string
  msg_type: string
}

export interface NinaWarningsResponse {
  ars: string
  warnings: NinaNormalizedWarning[]
  fetched_at: string
  source: 'live' | 'cache'
}

interface ArsState {
  warnings: ReturnType<typeof ref<NinaNormalizedWarning[]>>
  loading: ReturnType<typeof ref<boolean>>
  error: ReturnType<typeof ref<string | null>>
  timer: number | null
  consumers: number
}

const arsStateMap = new Map<string, ArsState>()

function getApiBase(): string {
  return (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'
}

function buildState(): ArsState {
  return {
    warnings: ref<NinaNormalizedWarning[]>([]),
    loading: ref(true),
    error: ref<string | null>(null),
    timer: null,
    consumers: 0,
  }
}

async function fetchWarnings(ars: string, state: ArsState): Promise<void> {
  state.loading.value = true
  state.error.value = null
  try {
    const response = await fetch(`${getApiBase()}/api/v1/nina/${ars}`)
    if (!response.ok) {
      state.error.value = `Fehler ${response.status}`
      state.warnings.value = []
      return
    }
    const data: NinaWarningsResponse = await response.json()
    state.warnings.value = data.warnings
  } catch {
    state.error.value = 'Keine Verbindung'
    state.warnings.value = []
  } finally {
    state.loading.value = false
  }
}

export function useNinaWarnings(ars: string, refreshInterval = 300_000) {
  let state = arsStateMap.get(ars)
  if (!state) {
    state = buildState()
    arsStateMap.set(ars, state)
  }

  state.consumers++

  if (state.consumers === 1) {
    void fetchWarnings(ars, state)
    state.timer = window.setInterval(() => {
      void fetchWarnings(ars, state!)
    }, refreshInterval)
  }

  const capturedState = state

  function refresh(): void {
    void fetchWarnings(ars, capturedState)
  }

  function unmount(): void {
    capturedState.consumers--
    if (capturedState.consumers <= 0) {
      if (capturedState.timer !== null) {
        window.clearInterval(capturedState.timer)
        capturedState.timer = null
      }
      arsStateMap.delete(ars)
    }
  }

  return {
    warnings: readonly(capturedState.warnings),
    loading: readonly(capturedState.loading),
    error: readonly(capturedState.error),
    refresh,
    unmount,
  }
}

export function _resetNinaStateForTesting(): void {
  for (const state of arsStateMap.values()) {
    if (state.timer !== null) {
      window.clearInterval(state.timer)
    }
  }
  arsStateMap.clear()
}
