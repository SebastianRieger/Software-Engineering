import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import GestureContextHUD from '../../components/manager/GestureContextHUD.vue'
import type { InteractionState } from '../../composables/useInteractionState'

function mountHud(interactionState: InteractionState) {
  return mount(GestureContextHUD, {
    props: {
      interactionState,
    },
  })
}

describe('GestureContextHUD', () => {
  it('shows grid navigation on the HomeScreen', () => {
    const wrapper = mountHud('home')

    expect(wrapper.text()).toContain('Grid öffnen')
    expect(wrapper.text()).not.toContain('Edit starten')
  })

  it('shows only executable empty-cell edit actions', () => {
    const wrapper = mountHud('edit-empty')

    expect(wrapper.text()).toContain('Shop öffnen')
    expect(wrapper.text()).toContain('Beenden')
    expect(wrapper.text()).not.toContain('Skalieren')
    expect(wrapper.text()).not.toContain('Löschen')
  })

  it('shows widget actions for occupied focused cells', () => {
    const wrapper = mountHud('edit-widget')

    expect(wrapper.text()).toContain('Greifen')
    expect(wrapper.text()).toContain('Skalieren')
    expect(wrapper.text()).toContain('Löschen')
  })
})
