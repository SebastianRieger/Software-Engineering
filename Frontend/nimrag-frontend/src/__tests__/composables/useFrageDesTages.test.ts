import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'

vi.mock('@/services/trivia', () => ({ getTrivia: vi.fn() }))

import { getTrivia } from '@/services/trivia'
import { useFrageDesTages } from '@/composables/useFrageDesTages'

const mockedGetTrivia = vi.mocked(getTrivia)

function mountComposable() {
  let api: ReturnType<typeof useFrageDesTages>
  const Comp = defineComponent({
    setup() { api = useFrageDesTages(); return {} },
    template: '<div />',
  })
  const wrapper = mount(Comp)
  return { wrapper, get api() { return api! } }
}

beforeEach(() => { mockedGetTrivia.mockReset() })
afterEach(() => { vi.useRealTimers() })

describe('useFrageDesTages', () => {
  it('loads question on mount', async () => {
    const question = { question: 'What is 2+2?', answer: '4' }
    mockedGetTrivia.mockResolvedValue(question)
    const { api, wrapper } = mountComposable()
    await flushPromises()
    expect(api.question.value).toEqual(question)
    expect(api.isLoading.value).toBe(false)
    wrapper.unmount()
  })

  it('sets error when fetch fails', async () => {
    mockedGetTrivia.mockRejectedValue(new Error('timeout'))
    const { api, wrapper } = mountComposable()
    await flushPromises()
    expect(api.error.value).toBe('timeout')
    wrapper.unmount()
  })

  it('reveal() sets isRevealed to true', async () => {
    mockedGetTrivia.mockResolvedValue({ question: 'Q', answer: 'A' })
    const { api, wrapper } = mountComposable()
    expect(api.isRevealed.value).toBe(false)
    api.reveal()
    expect(api.isRevealed.value).toBe(true)
    wrapper.unmount()
  })
})
