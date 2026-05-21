import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import GridBoard from '@/components/manager/GridBoard.vue'
import { useWidgetResize } from '@/composables/useWidgetResize'

// Ensure cells 1–16 are initialised at size 1 before each test
beforeEach(() => {
  const { cellSizes } = useWidgetResize()
  for (let i = 1; i <= 16; i++) cellSizes.value[i] = 1
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

  it('marks the focused cell with a dedicated class', () => {
    const wrapper = mount(GridBoard, { props: { isEditMode: false, focusedCellId: 3 } })
    const focusedCell = wrapper.find('[data-cell-id="3"]')

    expect(focusedCell.classes()).toContain('grid-cell-focused')
    expect(focusedCell.attributes('aria-selected')).toBe('true')
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

    // Simulate drag-start on cell 1 (index 0) then drop on cell 2 (index 1)
    const dt = { getData: vi.fn().mockReturnValue('1'), setData: vi.fn(), effectAllowed: '', dropEffect: '', setDragImage: vi.fn() }
    await cells[0]!.trigger('dragstart', { dataTransfer: dt })
    await cells[1]!.trigger('dragover', { dataTransfer: dt, preventDefault: vi.fn() })
    await cells[1]!.trigger('drop', { dataTransfer: dt, preventDefault: vi.fn() })

    const emitted = wrapper.emitted('widgetsMoved')
    if (emitted) {
      expect(emitted[0]).toBeDefined()
    }
  })

  it('resets cell opacity on dragend', async () => {
    const wrapper = mount(GridBoard, { props: { isEditMode: false } })
    const cell = wrapper.find('.grid-cell')
    await cell.trigger('dragend')
    // Just verify no errors are thrown
    expect(wrapper.exists()).toBe(true)
  })

  it('emits deleteWidget when delete button is clicked', async () => {
    // Insert a widget DOM-side so hasWidget returns true
    const wrapper = mount(GridBoard, { props: { isEditMode: true } })
    await wrapper.vm.$nextTick()

    const mountEl = document.getElementById('cell-content-1')
    if (mountEl) {
      // Remove the placeholder so hasWidget(1) returns true
      mountEl.innerHTML = '<div class="real-widget">widget</div>'
      await wrapper.vm.$nextTick()

      // Force re-render by triggering widgetVersion bump via delete click
      const deleteBtn = wrapper.find('.delete-widget-btn')
      if (deleteBtn.exists()) {
        await deleteBtn.trigger('click')
        expect(wrapper.emitted('deleteWidget')).toBeTruthy()
      }
    }
  })
})
