import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WeatherWidget from '@/components/widgets/WeatherWidget.vue'

describe('WeatherWidget', () => {
  it('renders without errors', () => {
    const wrapper = mount(WeatherWidget)
    expect(wrapper.exists()).toBe(true)
  })

  it('displays the "Wetter" heading', () => {
    const wrapper = mount(WeatherWidget)
    expect(wrapper.find('h3').text()).toBe('Wetter')
  })

  it('shows the city name', () => {
    const wrapper = mount(WeatherWidget)
    expect(wrapper.text()).toContain('Karlsruhe')
  })

  it('shows the temperature', () => {
    const wrapper = mount(WeatherWidget)
    expect(wrapper.text()).toContain('21°C')
  })

  it('shows the condition', () => {
    const wrapper = mount(WeatherWidget)
    expect(wrapper.text()).toContain('Wolkig')
  })
})
