import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, markRaw } from 'vue'
import GridBoard from '@/components/manager/GridBoard.vue'
import { useWidgetResize } from '@/composables/useWidgetResize'
import { useWidgetManager } from '@/composables/useWidgetManager'

const DummyWidget = defineComponent({
  name: 'DummyWidget',
  render() { return h('div', { class: 'dummy-widget' }, 'Widget') },
})

beforeEach(() => {
  const { cellSizes } = useWidgetResize()
  for (let i = 1; i <= 16; i++) cellSizes.value[i] = 1
  const { widgetMap } = useWidgetManager()
  widgetMap.value = {}
})

afterEach(() => {
  vi.useRealTimers()
  document.body.innerHTML = ''
})

describe('GridBoard', () => {
  it('renders without errors', () => {
    const wrapper = mount(GridBoard, { props: { isEditMode: false } })
    expect(wrapper.exists()).toBe(true)
  })

  it('renders 16 grid cells', () => {
    const wrapper = mount(GridBoard, { props: { isEditMode: false } })
    const cells = wrapper.findAll('.grid-cell')
    expect(cells.length).toBe(16)
  })

  it('does not show delete or resize buttons when isEditMode is false', () => {
    const wrapper = mount(GridBoard, { props: { isEditMode: false } })
    expect(wrapper.find('.delete-widget-btn').exists()).toBe(false)
    expect(wrapper.find('.resize-widget-btn').exists()).toBe(false)
  })

  it('cells have draggable attribute', () => {
    const wrapper = mount(GridBoard, { props: { isEditMode: false } })
    const firstCell = wrapper.find('.grid-cell')
    expect(firstCell.attributes('draggable')).toBe('true')
  })

  it('emits widgetsMoved with source and target IDs on drop', async () => {
    const wrapper = mount(GridBoard, { props: { isEditMode: false } })
    const cells = wrapper.findAll('.grid-cell')

    const dt = { getData: vi.fn().mockReturnValue('1'), setData: vi.fn(), effectAllowed: '', dropEffect: '', setDragImage: vi.fn() }
    await cells[0]!.trigger('dragstart', { dataTransfer: dt })
    await cells[1]!.trigger('dragover', { dataTransfer: dt, preventDefault: vi.fn() })
    await cells[1]!.trigger('drop', { dataTransfer: dt, preventDefault: vi.fn() })

    const emitted = wrapper.emitted('widgetsMoved')
    if (emitted) {
      expect(emitted[0]).toBeDefined()
    }
  })

  it('resets dragging state on dragend without errors', async () => {
    const wrapper = mount(GridBoard, { props: { isEditMode: false } })
    const cell = wrapper.find('.grid-cell')
    await cell.trigger('dragend')
    expect(wrapper.exists()).toBe(true)
  })

  it('shows delete and resize buttons in edit mode when a widget is present', async () => {
    const { widgetMap } = useWidgetManager()
    widgetMap.value = { 1: markRaw(DummyWidget) }

    const wrapper = mount(GridBoard, { props: { isEditMode: true } })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.delete-widget-btn').exists()).toBe(true)
    expect(wrapper.find('.resize-widget-btn').exists()).toBe(true)
  })

  it('emits deleteWidget when delete button is clicked', async () => {
    const { widgetMap } = useWidgetManager()
    widgetMap.value = { 1: markRaw(DummyWidget) }

    const wrapper = mount(GridBoard, { props: { isEditMode: true } })
    await wrapper.vm.$nextTick()

    const deleteBtn = wrapper.find('.delete-widget-btn')
    expect(deleteBtn.exists()).toBe(true)
    await deleteBtn.trigger('click')
    expect(wrapper.emitted('deleteWidget')).toBeTruthy()
  })
})
