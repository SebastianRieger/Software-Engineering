import { ref, onUnmounted } from 'vue'

const HOVER_DELAY_MS = 1000

export function useHoverTrigger() {
  const active = ref(false)
  const x = ref(0)
  const y = ref(0)

  let timer: ReturnType<typeof setTimeout> | null = null
  let pendingCallback: (() => void) | null = null

  function start(event: MouseEvent, callback: () => void) {
    if (timer) clearTimeout(timer)
    x.value = event.clientX
    y.value = event.clientY
    active.value = true
    pendingCallback = callback
    timer = setTimeout(() => {
      timer = null
      active.value = false
      const cb = pendingCallback
      pendingCallback = null
      cb?.()
    }, HOVER_DELAY_MS)
  }

  function cancel() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    active.value = false
    pendingCallback = null
  }

  function move(event: MouseEvent) {
    if (active.value) {
      x.value = event.clientX
      y.value = event.clientY
    }
  }

  onUnmounted(cancel)

  return { active, x, y, start, cancel, move }
}
