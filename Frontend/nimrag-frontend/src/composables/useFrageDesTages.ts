import { ref, onMounted } from 'vue'
import { getTrivia } from '../services/trivia'
import type { TriviaQuestion } from '../types/trivia'

export function useFrageDesTages() {
  const question = ref<TriviaQuestion | null>(null)
  const isLoading = ref(true)
  const error = ref<string | null>(null)
  const isRevealed = ref(false)

  async function load() {
    try {
      isLoading.value = true
      error.value = null
      question.value = await getTrivia()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Fehler beim Laden'
    } finally {
      isLoading.value = false
    }
  }

  function reveal() {
    isRevealed.value = true
  }

  onMounted(() => {
    void load()
  })

  return { question, isLoading, error, isRevealed, reveal }
}
