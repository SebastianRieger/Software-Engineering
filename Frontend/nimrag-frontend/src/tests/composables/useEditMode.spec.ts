/**
 * useEditMode.spec.ts
 * Unit tests for useEditMode composable
 * Tests edit mode toggle, keyboard event handling, and lifecycle management
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useEditMode } from '@/composables/useEditMode';

describe('useEditMode composable', () => {
  describe('Initial State', () => {
    it('should initialize with edit mode disabled', () => {
      const { isEditMode } = useEditMode();

      expect(isEditMode.value).toBe(false);
    });
  });

  describe('toggleEditMode', () => {
    it('should toggle edit mode from false to true', () => {
      const { isEditMode, toggleEditMode } = useEditMode();

      expect(isEditMode.value).toBe(false);
      toggleEditMode();
      expect(isEditMode.value).toBe(true);
    });

    it('should toggle edit mode from true to false', () => {
      const { isEditMode, toggleEditMode } = useEditMode();

      toggleEditMode();
      expect(isEditMode.value).toBe(true);
      toggleEditMode();
      expect(isEditMode.value).toBe(false);
    });

    it('should toggle multiple times correctly', () => {
      const { isEditMode, toggleEditMode } = useEditMode();

      for (let i = 0; i < 5; i++) {
        toggleEditMode();
        expect(isEditMode.value).toBe(i % 2 === 0);
      }
    });
  });

  describe('handleKeydown', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('should call onShopToggle when "e" key is pressed', () => {
      const { handleKeydown } = useEditMode();
      const callbacks = {
        onShopToggle: vi.fn(),
        onShopNavigate: vi.fn(),
        onEditModeToggle: vi.fn(),
      };

      const event = new KeyboardEvent('keydown', { key: 'e' });
      handleKeydown(event, callbacks);

      expect(callbacks.onShopToggle).toHaveBeenCalledTimes(1);
      expect(callbacks.onShopNavigate).not.toHaveBeenCalled();
    });

    it('should toggle edit mode and call callback when "f" key is pressed', () => {
      const { isEditMode, handleKeydown } = useEditMode();
      const callbacks = {
        onShopToggle: vi.fn(),
        onShopNavigate: vi.fn(),
        onEditModeToggle: vi.fn(),
      };

      expect(isEditMode.value).toBe(false);
      const event = new KeyboardEvent('keydown', { key: 'f' });
      handleKeydown(event, callbacks);

      expect(isEditMode.value).toBe(true);
      expect(callbacks.onEditModeToggle).toHaveBeenCalledTimes(1);
    });

    it('should handle capital "F" key', () => {
      const { isEditMode, handleKeydown } = useEditMode();
      const callbacks = {
        onShopToggle: vi.fn(),
        onShopNavigate: vi.fn(),
        onEditModeToggle: vi.fn(),
      };

      const event = new KeyboardEvent('keydown', { key: 'F' });
      handleKeydown(event, callbacks);

      expect(isEditMode.value).toBe(true);
      expect(callbacks.onEditModeToggle).toHaveBeenCalledTimes(1);
    });

    it('should call onShopToggle when Escape key is pressed', () => {
      const { handleKeydown } = useEditMode();
      const callbacks = {
        onShopToggle: vi.fn(),
        onShopNavigate: vi.fn(),
        onEditModeToggle: vi.fn(),
      };

      const event = new KeyboardEvent('keydown', { key: 'Escape' });
      handleKeydown(event, callbacks);

      expect(callbacks.onShopToggle).toHaveBeenCalledTimes(1);
    });

    it('should call onShopNavigate for arrow keys', () => {
      const { handleKeydown } = useEditMode();
      const callbacks = {
        onShopToggle: vi.fn(),
        onShopNavigate: vi.fn(),
        onEditModeToggle: vi.fn(),
      };

      const arrowKeys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'];

      arrowKeys.forEach((key) => {
        vi.clearAllMocks();
        const event = new KeyboardEvent('keydown', { key });
        handleKeydown(event, callbacks);

        expect(callbacks.onShopNavigate).toHaveBeenCalledWith(key);
      });
    });

    it('should call onShopNavigate for other keys', () => {
      const { handleKeydown } = useEditMode();
      const callbacks = {
        onShopToggle: vi.fn(),
        onShopNavigate: vi.fn(),
      };

      const event = new KeyboardEvent('keydown', { key: 'a' });
      handleKeydown(event, callbacks);

      expect(callbacks.onShopNavigate).toHaveBeenCalledWith('a');
    });

    it('should handle optional onEditModeToggle callback', () => {
      const { handleKeydown } = useEditMode();
      const callbacks = {
        onShopToggle: vi.fn(),
        onShopNavigate: vi.fn(),
      };

      const event = new KeyboardEvent('keydown', { key: 'f' });
      expect(() => {
        handleKeydown(event, callbacks);
      }).not.toThrow();
    });
  });

  describe('setupKeyboardListener', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('should return a function with proper structure', () => {
      const { setupKeyboardListener } = useEditMode();

      expect(typeof setupKeyboardListener).toBe('function');
    });

    it('should not throw when called with valid callbacks', () => {
      const { setupKeyboardListener } = useEditMode();
      const callbacks = {
        onShopToggle: vi.fn(),
        onShopNavigate: vi.fn(),
      };

      expect(() => {
        setupKeyboardListener(callbacks);
      }).not.toThrow();
    });
  });

  describe('Integration', () => {
    it('should maintain state across multiple operations', () => {
      const { isEditMode, toggleEditMode, handleKeydown } = useEditMode();
      const callbacks = {
        onShopToggle: vi.fn(),
        onShopNavigate: vi.fn(),
        onEditModeToggle: vi.fn(),
      };

      expect(isEditMode.value).toBe(false);

      toggleEditMode();
      expect(isEditMode.value).toBe(true);

      const event = new KeyboardEvent('keydown', { key: 'f' });
      handleKeydown(event, callbacks);
      expect(isEditMode.value).toBe(false);

      callbacks.onEditModeToggle?.();
      expect(callbacks.onEditModeToggle).toHaveBeenCalled();
    });
  });
});

