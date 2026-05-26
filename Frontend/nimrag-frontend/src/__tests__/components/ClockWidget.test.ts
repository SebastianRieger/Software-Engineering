import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, shallowMount } from '@vue/test-utils'
import { ref } from 'vue'
import ClockWidget from '@/components/widgets/ClockWidget.vue'
import AnalogClock from '@/components/internal/AnalogClock.vue'
import { useClockWidgetMode } from '@/composables/useClockWidgetMode'
import type { CellSize } from '@/composables/useWidgetResize'

describe('ClockWidget', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders without errors', () => {
    const wrapper = mount(ClockWidget)
    expect(wrapper.exists()).toBe(true)
  })

  it('displays a formatted time string', () => {
    const wrapper = mount(ClockWidget)
    // The time element should contain at least a colon (HH:MM)
    const timeEl = wrapper.find('p')
    expect(timeEl.exists()).toBe(true)
    expect(timeEl.text()).toMatch(/\d{1,2}:\d{2}/)
  })

  it('updates the displayed time after 1 second', async () => {
    const before = new Date()
    vi.setSystemTime(before)

    const wrapper = mount(ClockWidget)
    const initialText = wrapper.find('p').text()

    vi.advanceTimersByTime(1000)
    await wrapper.vm.$nextTick()

    const afterText = wrapper.find('p').text()
    // After advancing 1 second the formatted time string changes
    const afterDate = new Date(before.getTime() + 1000)
    expect(afterText).toBe(afterDate.toLocaleTimeString())
    expect(afterText).not.toBe(initialText)
  })

  it('clears the interval on unmount', () => {
    const clearSpy = vi.spyOn(window, 'clearInterval')
    const wrapper = mount(ClockWidget)
    wrapper.unmount()
    expect(clearSpy).toHaveBeenCalled()
  })

  it('uses 8rem font size when cellSize is 4 (2×2 grid cell)', () => {
    const wrapper = mount(ClockWidget, {
      global: {
        provide: {
          cellId: 1,
          cellSizes: ref({ 1: 4 as CellSize }),
        },
      },
    })
    const p = wrapper.find('p')
    expect(p.attributes('style')).toContain('8rem')
  })

  it('uses 6rem font size when cellSize is 2 (2×1 grid cell)', () => {
    const wrapper = mount(ClockWidget, {
      global: {
        provide: {
          cellId: 1,
          cellSizes: ref({ 1: 2 as CellSize }),
        },
      },
    })
    const p = wrapper.find('p')
    expect(p.attributes('style')).toContain('6rem')
  })

  it('shows AnalogClock when cellId is non-zero and analog mode is active', async () => {
    const { clockAnalogMode } = useClockWidgetMode()
    clockAnalogMode.value = true

    // shallowMount stubs AnalogClock to avoid canvas errors in jsdom
    const wrapper = shallowMount(ClockWidget, {
      global: {
        provide: {
          cellId: 1,
          cellSizes: ref({ 1: 1 as CellSize }),
        },
      },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.findComponent(AnalogClock).exists()).toBe(true)
    expect(wrapper.find('p').exists()).toBe(false)

    // Cleanup singleton state
    clockAnalogMode.value = false
  })
})
