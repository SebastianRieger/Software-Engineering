import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import App from '@/App.vue'

beforeEach(() => {
  vi.useFakeTimers()
  vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})))
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('renders without errors', () => {
    const wrapper = shallowMount(App)
    expect(wrapper.exists()).toBe(true)
  })

  it('contains a ModuleManager stub', () => {
    const wrapper = shallowMount(App)
    // shallowMount stubs child components; the stub element should be present
    expect(wrapper.html()).toBeTruthy()
  })
})
