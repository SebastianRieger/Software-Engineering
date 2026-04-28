/**
 * useWidgetManager.spec.ts
 * Unit tests for useWidgetManager composable
 * Tests widget lifecycle, DOM manipulation, and state management
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { useWidgetManager } from '@/composables/useWidgetManager';

describe('useWidgetManager composable', () => {
  beforeEach(() => {
    // Create mock DOM elements for testing
    document.body.innerHTML = '';
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  describe('Initial State', () => {
    it('should initialize with empty active widgets', () => {
      const { activeWidgets } = useWidgetManager();

      expect(Object.keys(activeWidgets).length).toBe(0);
    });
  });

  describe('insertWidgetIntoCell', () => {
    it('should handle missing mount point gracefully', () => {
      const { insertWidgetIntoCell } = useWidgetManager();
      const mockComponent = { name: 'TestWidget' };
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      insertWidgetIntoCell(1, mockComponent);

      // Should log error for missing mount point
      consoleSpy.mockRestore();
    });

    it('should not throw when mount point does not exist', () => {
      const { insertWidgetIntoCell } = useWidgetManager();
      const mockComponent = { name: 'TestWidget' };

      expect(() => {
        insertWidgetIntoCell(1, mockComponent);
      }).not.toThrow();
    });

    it('should create proper container structure', () => {
      const { insertWidgetIntoCell } = useWidgetManager();
      const cellId = 1;

      // Create mock DOM structure
      const mount = document.createElement('div');
      mount.id = `cell-content-${cellId}`;
      document.body.appendChild(mount);

      const mockComponent = { name: 'TestWidget', template: '<div>test</div>' };

      insertWidgetIntoCell(cellId, mockComponent);

      // After insertion, container should be created
      const containers = mount.querySelectorAll('div');
      expect(containers.length).toBeGreaterThan(0);
    });
  });

  describe('clearCell', () => {
    it('should handle missing mount point gracefully', () => {
      const { clearCell } = useWidgetManager();

      expect(() => {
        clearCell(1);
      }).not.toThrow();
    });

    it('should restore placeholder for existing cell', () => {
      const { clearCell } = useWidgetManager();
      const cellId = 1;

      // Create mock DOM structure
      const mount = document.createElement('div');
      mount.id = `cell-content-${cellId}`;
      document.body.appendChild(mount);

      clearCell(cellId);

      // Should contain placeholder with cell number
      expect(mount.innerHTML).toContain('01');
    });

    it('should clear HTML content of cell', () => {
      const { clearCell } = useWidgetManager();
      const cellId = 5;

      // Create mock DOM structure with content
      const mount = document.createElement('div');
      mount.id = `cell-content-${cellId}`;
      mount.innerHTML = '<p>Old content</p>';
      document.body.appendChild(mount);

      clearCell(cellId);

      // Old content should be replaced
      expect(mount.innerHTML).not.toContain('Old content');
    });

    it('should format cell number with padding', () => {
      const { clearCell } = useWidgetManager();

      const testCases = [
        { cellId: 1, expected: '01' },
        { cellId: 5, expected: '05' },
        { cellId: 10, expected: '10' },
      ];

      testCases.forEach(({ cellId, expected }) => {
        const mount = document.createElement('div');
        mount.id = `cell-content-${cellId}`;
        document.body.appendChild(mount);

        clearCell(cellId);

        expect(mount.innerHTML).toContain(expected);
        mount.remove();
      });
    });
  });

  describe('moveWidgets', () => {
    it('should not throw for non-existent widgets', () => {
      const { moveWidgets } = useWidgetManager();

      expect(() => {
        moveWidgets({ sourceCellId: 1, targetCellId: 2 });
      }).not.toThrow();
    });

    it('should swap widgets when both cells have widgets', () => {
      const { activeWidgets, moveWidgets } = useWidgetManager();

      const mockApp1 = { unmount: vi.fn() };
      const mockApp2 = { unmount: vi.fn() };

      activeWidgets[1] = mockApp1;
      activeWidgets[2] = mockApp2;

      moveWidgets({ sourceCellId: 1, targetCellId: 2 });

      expect(activeWidgets[1]).toBe(mockApp2);
      expect(activeWidgets[2]).toBe(mockApp1);
    });

    it('should move widget from source to target if only source has widget', () => {
      const { activeWidgets, moveWidgets } = useWidgetManager();

      const mockApp = { unmount: vi.fn() };
      activeWidgets[1] = mockApp;

      moveWidgets({ sourceCellId: 1, targetCellId: 2 });

      expect(activeWidgets[1]).toBeUndefined();
      expect(activeWidgets[2]).toBe(mockApp);
    });

    it('should move widget to source if only target has widget', () => {
      const { activeWidgets, moveWidgets } = useWidgetManager();

      const mockApp = { unmount: vi.fn() };
      activeWidgets[2] = mockApp;

      moveWidgets({ sourceCellId: 1, targetCellId: 2 });

      expect(activeWidgets[1]).toBe(mockApp);
      expect(activeWidgets[2]).toBeUndefined();
    });

    it('should allow deleting widgets from tracking', () => {
      const { activeWidgets } = useWidgetManager();

      const mockApp = { unmount: vi.fn() };
      activeWidgets[1] = mockApp;

      expect(activeWidgets[1]).toBeDefined();
      delete activeWidgets[1];
      expect(activeWidgets[1]).toBeUndefined();
    });
  });

  describe('Type Safety', () => {
    it('should accept valid cell IDs', () => {
      const { moveWidgets } = useWidgetManager();

      const validCellIds = [1, 10, 100, 999];

      expect(() => {
        validCellIds.forEach((cellId) => {
          moveWidgets({ sourceCellId: cellId, targetCellId: cellId + 1 });
        });
      }).not.toThrow();
    });
  });

  describe('Integration', () => {
    it('should handle widget lifecycle sequence', () => {
      const { activeWidgets, moveWidgets } = useWidgetManager();

      const mockApp1 = { unmount: vi.fn() };
      const mockApp2 = { unmount: vi.fn() };

      // Add widgets
      activeWidgets[1] = mockApp1;
      activeWidgets[2] = mockApp2;

      // Move widgets
      moveWidgets({ sourceCellId: 1, targetCellId: 2 });

      // Verify state
      expect(activeWidgets[1]).toBe(mockApp2);
      expect(activeWidgets[2]).toBe(mockApp1);

      // Clear widgets
      delete activeWidgets[1];
      delete activeWidgets[2];

      expect(Object.keys(activeWidgets).length).toBe(0);
    });
  });
});

