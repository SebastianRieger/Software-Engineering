import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'

vi.mock('@/services/fact', () => ({ getFact: vi.fn() }))

import { getFact } from '@/services/fact'
import { useFaktDesTages } from '@/composables/useFaktDesTages'

const mockedGetFact = vi.mocked(getFact)

function mountComposable() {
  let api: ReturnType<typeof useFaktDesTages>
  const Comp = defineComponent({
    setup() { api = useFaktDesTages(); return {} },
    template: '<div />',
  })
  const wrapper = mount(Comp)
  return { wrapper, get api() { return api! } }
}

beforeEach(() => { mockedGetFact.mockReset() })
afterEach(() => { vi.useRealTimers() })

describe('useFaktDesTages', () => {
  it('loads fact on mount', async () => {
    const fact = { fact: 'Honey never spoils.' }
    mockedGetFact.mockResolvedValue(fact)
    const { api, wrapper } = mountComposable()
    await flushPromises()
    expect(api.fact.value).toEqual(fact)
    expect(api.isLoading.value).toBe(false)
    wrapper.unmount()
  })

  it('sets error when fetch fails', async () => {
    mockedGetFact.mockRejectedValue(new Error('server error'))
    const { api, wrapper } = mountComposable()
    await flushPromises()
    expect(api.error.value).toBe('server error')
    wrapper.unmount()
  })
})
