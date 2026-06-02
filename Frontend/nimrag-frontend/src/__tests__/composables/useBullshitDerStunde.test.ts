import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'

vi.mock('@/services/bullshit', () => ({ getBullshit: vi.fn() }))

import { getBullshit } from '@/services/bullshit'
import { useBullshitDerStunde } from '@/composables/useBullshitDerStunde'

const mockedGetBullshit = vi.mocked(getBullshit)

function mountComposable() {
  let api: ReturnType<typeof useBullshitDerStunde>
  const Comp = defineComponent({
    setup() { api = useBullshitDerStunde(); return {} },
    template: '<div />',
  })
  const wrapper = mount(Comp)
  return { wrapper, get api() { return api! } }
}

beforeEach(() => {
  vi.useFakeTimers()
  mockedGetBullshit.mockReset()
})
afterEach(() => { vi.useRealTimers() })

describe('useBullshitDerStunde', () => {
  it('loads data on mount', async () => {
    const phrase = { phrase: 'Leverage synergies' }
    mockedGetBullshit.mockResolvedValue(phrase)
    const { api, wrapper } = mountComposable()
    await flushPromises()
    expect(mockedGetBullshit).toHaveBeenCalledOnce()
    expect(api.data.value).toEqual(phrase)
    expect(api.isLoading.value).toBe(false)
    wrapper.unmount()
  })

  it('sets error when fetch fails', async () => {
    mockedGetBullshit.mockRejectedValue(new Error('network fail'))
    const { api, wrapper } = mountComposable()
    await flushPromises()
    expect(api.error.value).toBe('network fail')
    expect(api.isLoading.value).toBe(false)
    wrapper.unmount()
  })

  it('clears timers on unmount without errors', async () => {
    mockedGetBullshit.mockResolvedValue({ phrase: 'test' })
    const { wrapper } = mountComposable()
    await vi.runAllTicks()
    expect(() => wrapper.unmount()).not.toThrow()
  })
})
