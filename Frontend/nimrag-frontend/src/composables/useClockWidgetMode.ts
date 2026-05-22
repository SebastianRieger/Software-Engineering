import { ref } from 'vue'

const clockAnalogMode = ref(false)

export function useClockWidgetMode() {
  const toggleClockMode = () => {
    clockAnalogMode.value = !clockAnalogMode.value
  }

  return {
    clockAnalogMode,
    toggleClockMode,
  }
}
