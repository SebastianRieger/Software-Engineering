import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

// Minimaler Smoke-Test – prüft, dass die Vue-Testumgebung funktioniert.
// Komponentenspezifische Tests sollten neben den jeweiligen .vue-Dateien abgelegt werden.

const StubComponent = defineComponent({
  render: () => h('div', 'Nimrag'),
})

describe('Vue Testumgebung', () => {
  it('mounted eine Komponente ohne Fehler', () => {
    const wrapper = mount(StubComponent)
    expect(wrapper.exists()).toBe(true)
    expect(wrapper.text()).toBe('Nimrag')
  })

  it('gibt korrekten HTML-Inhalt zurück', () => {
    const wrapper = mount(StubComponent)
    expect(wrapper.html()).toContain('Nimrag')
  })
})
