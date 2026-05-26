import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ClockWidget from '@/components/widgets/ClockWidget.vue'

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
})
