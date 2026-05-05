// @vitest-environment jsdom

import { defineComponent, markRaw } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import GridBoard from '../components/manager/GridBoard.vue'
import type { RenderedWidgetList } from '../types/widgets'

const DummyWidget = defineComponent({
  template: '<div class="dummy-widget">Widget</div>',
})

function buildWidgets(): RenderedWidgetList {
  return [
    {
      widget_id: 'weather-1-1',
      widget_type: 'weather',
      row: 1,
      col: 1,
      row_span: 1,
      col_span: 1,
      cell_id: 1,
      title: 'Wetter',
      settings: {},
      component: markRaw(DummyWidget),
      widgetProps: {},
    },
  ]
}

describe('GridBoard', () => {
  it('emits resize and delete events for the selected widget controls', async () => {
    const wrapper = mount(GridBoard, {
      props: {
        widgets: buildWidgets(),
        focusedCell: { row: 1, col: 1, widgetId: 'weather-1-1' },
        selectedWidgetId: 'weather-1-1',
        isArrangeMode: true,
      },
    })

    await wrapper.get('[data-action="resize-shrink"]').trigger('click')
    await wrapper.get('[data-action="resize-expand"]').trigger('click')
    await wrapper.get('[data-action="delete-widget"]').trigger('click')

    expect(wrapper.emitted('resizeWidget')).toEqual([
      [{ widgetId: 'weather-1-1', mode: 'shrink' }],
      [{ widgetId: 'weather-1-1', mode: 'expand' }],
    ])
    expect(wrapper.emitted('deleteWidget')).toEqual([
      [{ widgetId: 'weather-1-1' }],
    ])
  })

  it('keeps widget action controls hidden for unfocused and unselected widgets', () => {
    const wrapper = mount(GridBoard, {
      props: {
        widgets: buildWidgets(),
        focusedCell: { row: 2, col: 2, widgetId: null },
        selectedWidgetId: null,
        isArrangeMode: false,
      },
    })

    expect(wrapper.find('[data-action="resize-expand"]').exists()).toBe(false)
    expect(wrapper.find('[data-action="delete-widget"]').exists()).toBe(false)
  })
})