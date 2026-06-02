import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'

vi.mock('@/services/meme', () => ({ getMemes: vi.fn() }))

import { getMemes } from '@/services/meme'
import { useRandomMeme } from '@/composables/useRandomMeme'

const mockedGetMemes = vi.mocked(getMemes)

function mountComposable() {
  let api: ReturnType<typeof useRandomMeme>
  const Comp = defineComponent({
    setup() { api = useRandomMeme(); return {} },
    template: '<div />',
  })
  const wrapper = mount(Comp)
  return { wrapper, get api() { return api! } }
}

beforeEach(() => {
  vi.useFakeTimers()
  mockedGetMemes.mockReset()
})
afterEach(() => { vi.useRealTimers() })

describe('useRandomMeme', () => {
  it('loads memes on mount', async () => {
    const memes = [{ url: 'http://example.com/meme.jpg', title: 'test' }]
    mockedGetMemes.mockResolvedValue({ memes })
    const { api, wrapper } = mountComposable()
    await flushPromises()
    expect(api.memes.value).toEqual(memes)
    expect(api.isLoading.value).toBe(false)
    wrapper.unmount()
  })

  it('sets error when fetch fails', async () => {
    mockedGetMemes.mockRejectedValue(new Error('fetch error'))
    const { api, wrapper } = mountComposable()
    await flushPromises()
    expect(api.error.value).toBe('fetch error')
    wrapper.unmount()
  })

  it('onImageError() triggers a reload', async () => {
    mockedGetMemes.mockResolvedValue({ memes: [] })
    const { api, wrapper } = mountComposable()
    await flushPromises()
    mockedGetMemes.mockClear()
    await api.onImageError(0)
    expect(mockedGetMemes).toHaveBeenCalledOnce()
    wrapper.unmount()
  })

  it('clears interval on unmount', async () => {
    mockedGetMemes.mockResolvedValue({ memes: [] })
    const { wrapper } = mountComposable()
    await vi.runAllTicks()
    expect(() => wrapper.unmount()).not.toThrow()
  })
})
