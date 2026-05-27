import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TemplateWidget from '@/components/widgets/TemplateWidget.vue'

describe('TemplateWidget', () => {
  it('renders without errors', () => {
    const wrapper = mount(TemplateWidget)
    expect(wrapper.exists()).toBe(true)
  })

  it('displays the "Template" heading', () => {
    const wrapper = mount(TemplateWidget)
    expect(wrapper.find('h3').text()).toBe('Template')
  })
})
