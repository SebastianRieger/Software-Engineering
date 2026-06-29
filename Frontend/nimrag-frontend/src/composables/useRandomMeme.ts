import { ref, onMounted, onUnmounted } from 'vue'
import { getMemes } from '../services/meme'
import type { MemeItem } from '../types/meme'

const REFRESH_INTERVAL_MS = 10 * 60 * 1000

export function useRandomMeme() {
  const memes = ref<MemeItem[]>([])
  const isLoading = ref(true)
  const error = ref<string | null>(null)

  let intervalId: ReturnType<typeof setInterval> | null = null
  let retryGuard = false

  async function load() {
    try {
      isLoading.value = true
      error.value = null
      const response = await getMemes()
      memes.value = response.memes
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Fehler beim Laden'
    } finally {
      isLoading.value = false
    }
  }

  async function onImageError(_index: number) {
    if (retryGuard || isLoading.value) return
    retryGuard = true
    await load()
    retryGuard = false
  }

  onMounted(() => {
    void load()
    intervalId = setInterval(() => void load(), REFRESH_INTERVAL_MS)
  })

  onUnmounted(() => {
    if (intervalId !== null) clearInterval(intervalId)
  })

  return { memes, isLoading, error, onImageError }
}
