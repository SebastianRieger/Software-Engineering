import { ref, onMounted } from 'vue'
import { getFact } from '../services/fact'
import type { DailyFact } from '../types/fact'

export function useFaktDesTages() {
  const fact = ref<DailyFact | null>(null)
  const isLoading = ref(true)
  const error = ref<string | null>(null)

  async function load() {
    try {
      isLoading.value = true
      error.value = null
      fact.value = await getFact()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Fehler beim Laden'
    } finally {
      isLoading.value = false
    }
  }

  onMounted(() => {
    void load()
  })

  return { fact, isLoading, error }
}
