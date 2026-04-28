/**
 * Composable and Component Integration Tests
 * Tests for interactions between components and composables
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useEditMode } from '@/composables/useEditMode';
import { useModuleShop } from '@/composables/useModuleShop';

describe('Composable Integration', () => {
  describe('useEditMode + useModuleShop Integration', () => {
    it('should work together for edit mode and shop control', () => {
      const editMode = useEditMode();
      const shop = useModuleShop();

      expect(editMode.isEditMode.value).toBe(false);
      expect(shop.isShopOpen.value).toBe(false);

      editMode.toggleEditMode();
      shop.openShop();

      expect(editMode.isEditMode.value).toBe(true);
      expect(shop.isShopOpen.value).toBe(true);
    });

    it('should maintain independent state', () => {
      const editMode1 = useEditMode();
      const editMode2 = useEditMode();

      editMode1.toggleEditMode();
      expect(editMode1.isEditMode.value).toBe(true);
      expect(editMode2.isEditMode.value).toBe(false);
    });
  });

  describe('Keyboard Event Handling with Shop', () => {
    it('should toggle shop on "e" key and edit mode on "f" key', () => {
      const editMode = useEditMode();
      const shop = useModuleShop();

      const callbacks = {
        onShopToggle: () => shop.toggleShop(),
        onShopNavigate: vi.fn(),
        onEditModeToggle: () => {
          // Edit mode is already toggled in handleKeydown
        },
      };

      // Press 'e' key - should toggle shop
      const eKey = new KeyboardEvent('keydown', { key: 'e' });
      editMode.handleKeydown(eKey, callbacks);

      expect(shop.isShopOpen.value).toBe(true);

      // Press 'f' key - should toggle edit mode
      const fKey = new KeyboardEvent('keydown', { key: 'f' });
      editMode.handleKeydown(fKey, callbacks);

      expect(editMode.isEditMode.value).toBe(true);
    });

    it('should close shop on Escape key', () => {
      const editMode = useEditMode();
      const shop = useModuleShop();

      shop.openShop();
      expect(shop.isShopOpen.value).toBe(true);

      const callbacks = {
        onShopToggle: () => shop.toggleShop(),
        onShopNavigate: vi.fn(),
      };

      const escapeKey = new KeyboardEvent('keydown', { key: 'Escape' });
      editMode.handleKeydown(escapeKey, callbacks);

      expect(shop.isShopOpen.value).toBe(false);
    });
  });

  describe('Shop Widget Addition Flow', () => {
    it('should complete widget addition workflow', () => {
      const shop = useModuleShop();
      const addedWidgets: any[] = [];

      const insertCallback = (cellId: number, component: any) => {
        addedWidgets.push({ cellId, component });
      };

      const mockWidget = { name: 'TestWidget' };

      shop.openShop();
      expect(shop.isShopOpen.value).toBe(true);

      shop.addWidget(1, mockWidget, insertCallback);
      expect(addedWidgets.length).toBe(1);
      expect(addedWidgets[0].cellId).toBe(1);

      shop.closeShop();
      expect(shop.isShopOpen.value).toBe(false);
    });
  });
});

