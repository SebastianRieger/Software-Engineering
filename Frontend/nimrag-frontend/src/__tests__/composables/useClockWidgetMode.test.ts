import { describe, expect, it } from 'vitest'
import { useClockWidgetMode } from '@/composables/useClockWidgetMode'

describe('useClockWidgetMode', () => {
  it('toggleClockMode() flips clockAnalogMode', () => {
    const { clockAnalogMode, toggleClockMode } = useClockWidgetMode()
    const initial = clockAnalogMode.value
    toggleClockMode()
    expect(clockAnalogMode.value).toBe(!initial)
    toggleClockMode()
    expect(clockAnalogMode.value).toBe(initial)
  })
})
