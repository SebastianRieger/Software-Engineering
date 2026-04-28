/**
 * TemplateWidget.spec.ts
 * Unit tests for TemplateWidget component
 * Tests the template widget functionality
 */

import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import TemplateWidget from '@/components/widgets/TemplateWidget.vue';

describe('TemplateWidget.vue', () => {
  describe('Rendering', () => {
    it('should render template widget without errors', () => {
      expect(() => {
        mount(TemplateWidget);
      }).not.toThrow();
    });

    it('should have card container', () => {
      const wrapper = mount(TemplateWidget);

      expect(wrapper.find('.card').exists()).toBe(true);
    });

    it('should apply correct styling classes', () => {
      const wrapper = mount(TemplateWidget);
      const card = wrapper.find('.card');

      expect(card.classes('card')).toBe(true);
      expect(card.classes('flex')).toBe(true);
      expect(card.classes('flex-col')).toBe(true);
    });
  });

  describe('Component Lifecycle', () => {
    it('should mount successfully', () => {
      const wrapper = mount(TemplateWidget);
      expect(wrapper.vm).toBeTruthy();
    });

    it('should unmount without errors', () => {
      const wrapper = mount(TemplateWidget);
      expect(() => {
        wrapper.unmount();
      }).not.toThrow();
    });
  });
});

