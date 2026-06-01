import { ref, onMounted, onUnmounted } from 'vue'
import { getBullshit } from '../services/bullshit'
import type { BullshitResponse } from '../types/bullshit'

function msToNextHour(): number {
  const now = new Date()
  const next = new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours() + 1, 0, 0, 0)
  return next.getTime() - now.getTime()
}

export function useBullshitDerStunde() {
  const data = ref<BullshitResponse | null>(null)
  const isLoading = ref(true)
  const error = ref<string | null>(null)

  let timeoutId: ReturnType<typeof setTimeout> | null = null
  let intervalId: ReturnType<typeof setInterval> | null = null

  async function load() {
    try {
      isLoading.value = true
      error.value = null
      data.value = await getBullshit()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Fehler beim Laden'
    } finally {
      isLoading.value = false
    }
  }

  onMounted(() => {
    void load()

    // Reload at the next full hour, then every hour on the dot
    timeoutId = setTimeout(() => {
      void load()
      intervalId = setInterval(() => void load(), 60 * 60 * 1000)
    }, msToNextHour())
  })

  onUnmounted(() => {
    if (timeoutId !== null) clearTimeout(timeoutId)
    if (intervalId !== null) clearInterval(intervalId)
  })

  return { data, isLoading, error }
}
