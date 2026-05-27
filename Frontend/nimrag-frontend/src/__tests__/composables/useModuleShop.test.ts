import { describe, it, expect, vi } from 'vitest'
import { useModuleShop } from '@/composables/useModuleShop'

describe('useModuleShop', () => {
  it('initializes with isShopOpen = false', () => {
    const { isShopOpen } = useModuleShop()
    expect(isShopOpen.value).toBe(false)
  })

  describe('toggleShop', () => {
    it('opens the shop when it is closed', () => {
      const { isShopOpen, toggleShop } = useModuleShop()
      toggleShop()
      expect(isShopOpen.value).toBe(true)
    })

    it('closes the shop when it is open', () => {
      const { isShopOpen, toggleShop } = useModuleShop()
      toggleShop()
      toggleShop()
      expect(isShopOpen.value).toBe(false)
    })
  })

  describe('openShop', () => {
    it('sets isShopOpen to true', () => {
      const { isShopOpen, openShop } = useModuleShop()
      openShop()
      expect(isShopOpen.value).toBe(true)
    })

    it('is idempotent when shop is already open', () => {
      const { isShopOpen, openShop } = useModuleShop()
      openShop()
      openShop()
      expect(isShopOpen.value).toBe(true)
    })
  })

  describe('closeShop', () => {
    it('sets isShopOpen to false', () => {
      const { isShopOpen, openShop, closeShop } = useModuleShop()
      openShop()
      closeShop()
      expect(isShopOpen.value).toBe(false)
    })

    it('is idempotent when shop is already closed', () => {
      const { isShopOpen, closeShop } = useModuleShop()
      closeShop()
      expect(isShopOpen.value).toBe(false)
    })
  })

  describe('addWidget', () => {
    it('calls insertCallback with the given cellId and component', () => {
      const { addWidget } = useModuleShop()
      const callback = vi.fn()
      const component = { template: '<div />' }
      addWidget(7, component, callback)
      expect(callback).toHaveBeenCalledOnce()
      expect(callback).toHaveBeenCalledWith(7, component)
    })

    it('passes different cellIds correctly', () => {
      const { addWidget } = useModuleShop()
      const callback = vi.fn()
      const comp = {}
      addWidget(1, comp, callback)
      addWidget(16, comp, callback)
      expect(callback).toHaveBeenCalledTimes(2)
      expect(callback).toHaveBeenNthCalledWith(1, 1, comp)
      expect(callback).toHaveBeenNthCalledWith(2, 16, comp)
    })
  })
})
