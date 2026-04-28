/**
 * state-management.spec.ts
 * Integration tests for state management
 * Tests reactive state handling and store operations
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { reactive, ref, computed } from 'vue';

/**
 * Mock Store for testing state management pattern
 */
interface AppState {
  widgets: Map<number, any>;
  editMode: boolean;
  selectedCell: number | null;
}

function createAppStore() {
  const state = reactive<AppState>({
    widgets: new Map(),
    editMode: false,
    selectedCell: null,
  });

  const getWidget = (cellId: number) => {
    return state.widgets.get(cellId);
  };

  const addWidget = (cellId: number, widget: any) => {
    state.widgets.set(cellId, widget);
  };

  const removeWidget = (cellId: number) => {
    state.widgets.delete(cellId);
  };

  const toggleEditMode = () => {
    state.editMode = !state.editMode;
  };

  const selectCell = (cellId: number | null) => {
    state.selectedCell = cellId;
  };

  const clearWidgets = () => {
    state.widgets.clear();
  };

  const getWidgetCount = computed(() => state.widgets.size);

  return {
    state,
    getWidget,
    addWidget,
    removeWidget,
    toggleEditMode,
    selectCell,
    clearWidgets,
    getWidgetCount,
  };
}

describe('State Management Integration', () => {
  let store: ReturnType<typeof createAppStore>;

  beforeEach(() => {
    store = createAppStore();
  });

  describe('Store Initialization', () => {
    it('should initialize with empty widgets', () => {
      expect(store.getWidgetCount.value).toBe(0);
    });

    it('should initialize with edit mode disabled', () => {
      expect(store.state.editMode).toBe(false);
    });

    it('should initialize with no selected cell', () => {
      expect(store.state.selectedCell).toBeNull();
    });
  });

  describe('Widget Management', () => {
    it('should add widget to store', () => {
      const mockWidget = { name: 'TestWidget' };
      store.addWidget(1, mockWidget);

      expect(store.getWidget(1)).toBe(mockWidget);
      expect(store.getWidgetCount.value).toBe(1);
    });

    it('should remove widget from store', () => {
      const mockWidget = { name: 'TestWidget' };
      store.addWidget(1, mockWidget);

      expect(store.getWidgetCount.value).toBe(1);
      store.removeWidget(1);
      expect(store.getWidgetCount.value).toBe(0);
    });

    it('should retrieve correct widget by cell ID', () => {
      const widget1 = { name: 'Widget1' };
      const widget2 = { name: 'Widget2' };

      store.addWidget(1, widget1);
      store.addWidget(2, widget2);

      expect(store.getWidget(1)).toBe(widget1);
      expect(store.getWidget(2)).toBe(widget2);
    });

    it('should return undefined for non-existent widget', () => {
      expect(store.getWidget(999)).toBeUndefined();
    });

    it('should handle multiple widget additions', () => {
      for (let i = 1; i <= 5; i++) {
        store.addWidget(i, { name: `Widget${i}` });
      }

      expect(store.getWidgetCount.value).toBe(5);
    });

    it('should clear all widgets', () => {
      store.addWidget(1, { name: 'Widget1' });
      store.addWidget(2, { name: 'Widget2' });

      expect(store.getWidgetCount.value).toBe(2);
      store.clearWidgets();
      expect(store.getWidgetCount.value).toBe(0);
    });

    it('should replace existing widget with new one', () => {
      const widget1 = { name: 'Old' };
      const widget2 = { name: 'New' };

      store.addWidget(1, widget1);
      store.addWidget(1, widget2);

      expect(store.getWidget(1)).toBe(widget2);
      expect(store.getWidgetCount.value).toBe(1);
    });
  });

  describe('Edit Mode Management', () => {
    it('should toggle edit mode on and off', () => {
      expect(store.state.editMode).toBe(false);

      store.toggleEditMode();
      expect(store.state.editMode).toBe(true);

      store.toggleEditMode();
      expect(store.state.editMode).toBe(false);
    });

    it('should toggle edit mode multiple times', () => {
      for (let i = 0; i < 5; i++) {
        store.toggleEditMode();
        expect(store.state.editMode).toBe(i % 2 === 0);
      }
    });
  });

  describe('Cell Selection', () => {
    it('should select a cell', () => {
      store.selectCell(1);

      expect(store.state.selectedCell).toBe(1);
    });

    it('should change selected cell', () => {
      store.selectCell(1);
      expect(store.state.selectedCell).toBe(1);

      store.selectCell(5);
      expect(store.state.selectedCell).toBe(5);
    });

    it('should deselect cell by passing null', () => {
      store.selectCell(1);
      expect(store.state.selectedCell).toBe(1);

      store.selectCell(null);
      expect(store.state.selectedCell).toBeNull();
    });

    it('should handle selection with zero as valid cell ID', () => {
      store.selectCell(0);

      expect(store.state.selectedCell).toBe(0);
    });
  });

  describe('Reactive State', () => {
    it('should update widget count reactively', () => {
      expect(store.getWidgetCount.value).toBe(0);

      store.addWidget(1, { name: 'Widget' });
      expect(store.getWidgetCount.value).toBe(1);

      store.addWidget(2, { name: 'Widget' });
      expect(store.getWidgetCount.value).toBe(2);

      store.removeWidget(1);
      expect(store.getWidgetCount.value).toBe(1);
    });

    it('should update edit mode reactively', () => {
      const isEditMode = computed(() => store.state.editMode);

      expect(isEditMode.value).toBe(false);

      store.toggleEditMode();
      expect(isEditMode.value).toBe(true);

      store.toggleEditMode();
      expect(isEditMode.value).toBe(false);
    });

    it('should update selected cell reactively', () => {
      const selectedCell = computed(() => store.state.selectedCell);

      expect(selectedCell.value).toBeNull();

      store.selectCell(1);
      expect(selectedCell.value).toBe(1);

      store.selectCell(null);
      expect(selectedCell.value).toBeNull();
    });
  });

  describe('Complex Operations', () => {
    it('should handle widget management with edit mode', () => {
      store.toggleEditMode();
      expect(store.state.editMode).toBe(true);

      store.addWidget(1, { name: 'Widget1' });
      store.selectCell(1);

      expect(store.getWidgetCount.value).toBe(1);
      expect(store.state.selectedCell).toBe(1);

      store.toggleEditMode();
      expect(store.state.editMode).toBe(false);
    });

    it('should maintain state consistency', () => {
      const widget1 = { name: 'Widget1', id: 1 };
      const widget2 = { name: 'Widget2', id: 2 };

      store.addWidget(1, widget1);
      store.addWidget(2, widget2);
      store.selectCell(1);
      store.toggleEditMode();

      // State should be consistent
      expect(store.getWidget(1)).toBe(widget1);
      expect(store.getWidget(2)).toBe(widget2);
      expect(store.state.selectedCell).toBe(1);
      expect(store.state.editMode).toBe(true);
      expect(store.getWidgetCount.value).toBe(2);
    });

    it('should handle rapid state changes', () => {
      for (let i = 1; i <= 10; i++) {
        store.addWidget(i, { name: `Widget${i}` });
        store.selectCell(i);
      }

      expect(store.getWidgetCount.value).toBe(10);
      expect(store.state.selectedCell).toBe(10);

      store.clearWidgets();
      expect(store.getWidgetCount.value).toBe(0);
    });
  });

  describe('Edge Cases', () => {
    it('should handle removing non-existent widget', () => {
      expect(() => {
        store.removeWidget(999);
      }).not.toThrow();
    });

    it('should handle clearing empty store', () => {
      expect(() => {
        store.clearWidgets();
      }).not.toThrow();

      expect(store.getWidgetCount.value).toBe(0);
    });

    it('should handle widget count with large cell IDs', () => {
      store.addWidget(999999, { name: 'BigId' });

      expect(store.getWidgetCount.value).toBe(1);
    });

    it('should handle null or undefined widgets gracefully', () => {
      store.addWidget(1, null);
      expect(store.getWidget(1)).toBe(null);

      store.addWidget(2, undefined);
      expect(store.getWidget(2)).toBeUndefined();
    });
  });
});

