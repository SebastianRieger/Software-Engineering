import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { useHoverTrigger } from '@/composables/useHoverTrigger'

function mountHover() {
  let api: ReturnType<typeof useHoverTrigger>
  const Comp = defineComponent({
    setup() { api = useHoverTrigger(); return {} },
    template: '<div />',
  })
  const wrapper = mount(Comp)
  return { wrapper, get api() { return api! } }
}

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers() })

describe('useHoverTrigger', () => {
  it('start() sets active and fires callback after delay', () => {
    const { api } = mountHover()
    const cb = vi.fn()
    api.start({ clientX: 10, clientY: 20 } as MouseEvent, cb)
    expect(api.active.value).toBe(true)
    vi.advanceTimersByTime(1000)
    expect(cb).toHaveBeenCalledOnce()
    expect(api.active.value).toBe(false)
  })

  it('cancel() clears the timer and deactivates', () => {
    const { api } = mountHover()
    const cb = vi.fn()
    api.start({ clientX: 0, clientY: 0 } as MouseEvent, cb)
    api.cancel()
    vi.advanceTimersByTime(1000)
    expect(cb).not.toHaveBeenCalled()
    expect(api.active.value).toBe(false)
  })

  it('move() updates coordinates while active', () => {
    const { api } = mountHover()
    api.start({ clientX: 5, clientY: 5 } as MouseEvent, vi.fn())
    api.move({ clientX: 50, clientY: 80 } as MouseEvent)
    expect(api.x.value).toBe(50)
    expect(api.y.value).toBe(80)
  })

  it('move() is a no-op when not active', () => {
    const { api } = mountHover()
    api.move({ clientX: 99, clientY: 99 } as MouseEvent)
    expect(api.x.value).toBe(0)
    expect(api.y.value).toBe(0)
  })

  it('cancel() is safe when no timer is running', () => {
    const { api } = mountHover()
    expect(() => api.cancel()).not.toThrow()
  })
})
