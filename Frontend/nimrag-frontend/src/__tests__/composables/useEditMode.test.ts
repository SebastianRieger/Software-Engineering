import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { useEditMode } from '@/composables/useEditMode'

// Mounts a test component that wires up the composable so lifecycle hooks
// (onMounted / onBeforeUnmount) execute in the correct Vue context.
function mountTestComponent(
  callbacks: Parameters<ReturnType<typeof useEditMode>['setupKeyboardListener']>[0]
) {
  let api: ReturnType<typeof useEditMode>

  const TestComp = defineComponent({
    setup() {
      api = useEditMode()
      api.setupKeyboardListener(callbacks)
      return {}
    },
    template: '<div />',
  })

  const wrapper = mount(TestComp)
  return { wrapper, get api() { return api! } }
}

afterEach(() => {
  // Ensure listeners from previous tests don't bleed through
  vi.restoreAllMocks()
})

describe('useEditMode', () => {
  describe('toggleEditMode', () => {
    it('starts with isEditMode = false', () => {
      const { isEditMode } = useEditMode()
      expect(isEditMode.value).toBe(false)
    })

    it('toggles false → true', () => {
      const { isEditMode, toggleEditMode } = useEditMode()
      toggleEditMode()
      expect(isEditMode.value).toBe(true)
    })

    it('toggles true → false', () => {
      const { isEditMode, toggleEditMode } = useEditMode()
      toggleEditMode()
      toggleEditMode()
      expect(isEditMode.value).toBe(false)
    })
  })

  describe('handleKeydown via setupKeyboardListener', () => {
    it('key "e" triggers onShopToggle', () => {
      const onShopToggle = vi.fn()
      const onShopNavigate = vi.fn()
      const { wrapper } = mountTestComponent({ onShopToggle, onShopNavigate })

      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'e' }))
      expect(onShopToggle).toHaveBeenCalledOnce()
      expect(onShopNavigate).not.toHaveBeenCalled()
      wrapper.unmount()
    })

    it('key "Escape" triggers onShopToggle', () => {
      const onShopToggle = vi.fn()
      const onShopNavigate = vi.fn()
      const { wrapper } = mountTestComponent({ onShopToggle, onShopNavigate })

      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
      expect(onShopToggle).toHaveBeenCalledOnce()
      wrapper.unmount()
    })

    it('key "f" toggles isEditMode and calls onEditModeToggle', () => {
      const onShopToggle = vi.fn()
      const onShopNavigate = vi.fn()
      const onEditModeToggle = vi.fn()
      const { wrapper, api } = mountTestComponent({ onShopToggle, onShopNavigate, onEditModeToggle })

      expect(api.isEditMode.value).toBe(false)
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'f' }))
      expect(api.isEditMode.value).toBe(true)
      expect(onEditModeToggle).toHaveBeenCalledOnce()
      wrapper.unmount()
    })

    it('key "F" also toggles isEditMode', () => {
      const onShopToggle = vi.fn()
      const onShopNavigate = vi.fn()
      const { wrapper, api } = mountTestComponent({ onShopToggle, onShopNavigate })

      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'F' }))
      expect(api.isEditMode.value).toBe(true)
      wrapper.unmount()
    })

    it('key "f" works without optional onEditModeToggle callback', () => {
      const onShopToggle = vi.fn()
      const onShopNavigate = vi.fn()
      const { wrapper, api } = mountTestComponent({ onShopToggle, onShopNavigate })

      // Should not throw even when onEditModeToggle is absent
      expect(() =>
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'f' }))
      ).not.toThrow()
      expect(api.isEditMode.value).toBe(true)
      wrapper.unmount()
    })

    it('arrow keys call onShopNavigate with the key string', () => {
      const onShopToggle = vi.fn()
      const onShopNavigate = vi.fn()
      const { wrapper } = mountTestComponent({ onShopToggle, onShopNavigate })

      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight' }))
      expect(onShopNavigate).toHaveBeenCalledWith('ArrowRight')

      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' }))
      expect(onShopNavigate).toHaveBeenCalledWith('ArrowLeft')
      wrapper.unmount()
    })

    it('unmounting removes the keyboard listener', () => {
      const onShopToggle = vi.fn()
      const onShopNavigate = vi.fn()
      const { wrapper } = mountTestComponent({ onShopToggle, onShopNavigate })

      wrapper.unmount()

      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'e' }))
      expect(onShopToggle).not.toHaveBeenCalled()
    })
  })
})
