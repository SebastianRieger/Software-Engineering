/**
 * useModuleShop.spec.ts
 * Unit tests for useModuleShop composable
 * Tests shop state management, open/close functionality, and widget addition
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useModuleShop } from '@/composables/useModuleShop';

describe('useModuleShop composable', () => {
  describe('Initial State', () => {
    it('should initialize with shop closed', () => {
      const { isShopOpen } = useModuleShop();

      expect(isShopOpen.value).toBe(false);
    });
  });

  describe('toggleShop', () => {
    it('should toggle shop from closed to open', () => {
      const { isShopOpen, toggleShop } = useModuleShop();

      expect(isShopOpen.value).toBe(false);
      toggleShop();
      expect(isShopOpen.value).toBe(true);
    });

    it('should toggle shop from open to closed', () => {
      const { isShopOpen, toggleShop } = useModuleShop();

      toggleShop();
      expect(isShopOpen.value).toBe(true);
      toggleShop();
      expect(isShopOpen.value).toBe(false);
    });

    it('should toggle shop multiple times', () => {
      const { isShopOpen, toggleShop } = useModuleShop();

      for (let i = 0; i < 6; i++) {
        toggleShop();
        expect(isShopOpen.value).toBe(i % 2 === 0);
      }
    });
  });

  describe('openShop', () => {
    it('should open a closed shop', () => {
      const { isShopOpen, openShop } = useModuleShop();

      expect(isShopOpen.value).toBe(false);
      openShop();
      expect(isShopOpen.value).toBe(true);
    });

    it('should keep shop open if already open', () => {
      const { isShopOpen, openShop } = useModuleShop();

      openShop();
      expect(isShopOpen.value).toBe(true);
      openShop();
      expect(isShopOpen.value).toBe(true);
    });

    it('should open shop multiple times without issues', () => {
      const { isShopOpen, openShop } = useModuleShop();

      for (let i = 0; i < 3; i++) {
        openShop();
        expect(isShopOpen.value).toBe(true);
      }
    });
  });

  describe('closeShop', () => {
    it('should close an open shop', () => {
      const { isShopOpen, openShop, closeShop } = useModuleShop();

      openShop();
      expect(isShopOpen.value).toBe(true);
      closeShop();
      expect(isShopOpen.value).toBe(false);
    });

    it('should keep shop closed if already closed', () => {
      const { isShopOpen, closeShop } = useModuleShop();

      expect(isShopOpen.value).toBe(false);
      closeShop();
      expect(isShopOpen.value).toBe(false);
    });

    it('should close shop multiple times without issues', () => {
      const { isShopOpen, closeShop } = useModuleShop();

      for (let i = 0; i < 3; i++) {
        closeShop();
        expect(isShopOpen.value).toBe(false);
      }
    });
  });

  describe('addWidget', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('should call insert callback with correct parameters', () => {
      const { addWidget } = useModuleShop();
      const mockCallback = vi.fn();
      const mockComponent = { name: 'TestWidget' };

      addWidget(1, mockComponent, mockCallback);

      expect(mockCallback).toHaveBeenCalledWith(1, mockComponent);
      expect(mockCallback).toHaveBeenCalledTimes(1);
    });

    it('should add widget to correct cell', () => {
      const { addWidget } = useModuleShop();
      const mockCallback = vi.fn();
      const mockComponent = { name: 'WeatherWidget' };

      addWidget(5, mockComponent, mockCallback);

      expect(mockCallback).toHaveBeenCalledWith(5, mockComponent);
    });

    it('should handle multiple widget additions', () => {
      const { addWidget } = useModuleShop();
      const mockCallback = vi.fn();

      const widgets = [
        { name: 'Widget1' },
        { name: 'Widget2' },
        { name: 'Widget3' },
      ];

      widgets.forEach((widget, index) => {
        addWidget(index + 1, widget, mockCallback);
      });

      expect(mockCallback).toHaveBeenCalledTimes(3);
    });

    it('should call callback with various cell IDs', () => {
      const { addWidget } = useModuleShop();
      const mockCallback = vi.fn();
      const mockComponent = { name: 'Widget' };

      const cellIds = [1, 5, 10, 99];

      cellIds.forEach((cellId) => {
        mockCallback.mockClear();
        addWidget(cellId, mockComponent, mockCallback);
        expect(mockCallback).toHaveBeenCalledWith(cellId, mockComponent);
      });
    });

    it('should handle complex component objects', () => {
      const { addWidget } = useModuleShop();
      const mockCallback = vi.fn();
      const complexComponent = {
        name: 'ComplexWidget',
        setup() {
          return { test: true };
        },
        template: '<div>Test</div>',
      };

      addWidget(1, complexComponent, mockCallback);

      expect(mockCallback).toHaveBeenCalledWith(1, complexComponent);
    });
  });

  describe('State Independence', () => {
    it('should maintain independent state for multiple instances', () => {
      const shop1 = useModuleShop();
      const shop2 = useModuleShop();

      shop1.openShop();
      expect(shop1.isShopOpen.value).toBe(true);
      expect(shop2.isShopOpen.value).toBe(false);

      shop2.openShop();
      expect(shop1.isShopOpen.value).toBe(true);
      expect(shop2.isShopOpen.value).toBe(true);

      shop1.closeShop();
      expect(shop1.isShopOpen.value).toBe(false);
      expect(shop2.isShopOpen.value).toBe(true);
    });
  });

  describe('Integration', () => {
    it('should work with toggle and open/close operations', () => {
      const { isShopOpen, toggleShop, openShop, closeShop } = useModuleShop();

      expect(isShopOpen.value).toBe(false);

      openShop();
      expect(isShopOpen.value).toBe(true);

      toggleShop();
      expect(isShopOpen.value).toBe(false);

      closeShop();
      expect(isShopOpen.value).toBe(false);

      toggleShop();
      expect(isShopOpen.value).toBe(true);
    });
  });
});

