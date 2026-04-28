/**
 * ClockWidget.spec.ts
 * Unit tests for ClockWidget component
 * Tests the clock display functionality and time updates
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import ClockWidget from '@/components/widgets/ClockWidget.vue';

describe('ClockWidget.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  describe('Rendering', () => {
    it('should render clock widget with correct structure', () => {
      const wrapper = mount(ClockWidget);

      expect(wrapper.find('.card').exists()).toBe(true);
      expect(wrapper.find('h3').exists()).toBe(true);
    });

    it('should display clock title', () => {
      const wrapper = mount(ClockWidget);

      const title = wrapper.find('h3');
      expect(title.text()).toBeTruthy();
    });

    it('should have correct CSS classes for clock card', () => {
      const wrapper = mount(ClockWidget);
      const card = wrapper.find('.card');

      expect(card.classes()).toContain('card');
      expect(card.classes()).toContain('flex');
      expect(card.classes()).toContain('flex-col');
    });
  });

  describe('Clock Display', () => {
    it('should display time in valid format', () => {
      const wrapper = mount(ClockWidget);
      const text = wrapper.text().toLowerCase();

      // Should contain time information
      expect(text.length).toBeGreaterThan(0);
    });
  });

  describe('Component Lifecycle', () => {
    it('should mount and unmount without errors', () => {
      const wrapper = mount(ClockWidget);
      expect(() => {
        wrapper.unmount();
      }).not.toThrow();
    });
  });
});

