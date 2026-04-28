/**
 * WeatherWidget.spec.ts
 * Unit tests for WeatherWidget component
 * Tests the weather display functionality and rendering
 */

import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import WeatherWidget from '@/components/widgets/WeatherWidget.vue';

describe('WeatherWidget.vue', () => {
  describe('Rendering', () => {
    it('should render weather widget with correct structure', () => {
      const wrapper = mount(WeatherWidget);

      expect(wrapper.find('.card').exists()).toBe(true);
      expect(wrapper.find('h3').exists()).toBe(true);
      expect(wrapper.find('p').exists()).toBe(true);
    });

    it('should display weather data correctly', () => {
      const wrapper = mount(WeatherWidget);

      expect(wrapper.text()).toContain('Wetter');
      expect(wrapper.text()).toContain('Karlsruhe');
      expect(wrapper.text()).toContain('Wolkig');
      expect(wrapper.text()).toContain('21°C');
    });

    it('should display city, condition and temperature in correct format', () => {
      const wrapper = mount(WeatherWidget);
      const paragraph = wrapper.find('p');

      expect(paragraph.text()).toBe('Karlsruhe · Wolkig · 21°C');
    });

    it('should have correct CSS classes for styling', () => {
      const wrapper = mount(WeatherWidget);
      const cardDiv = wrapper.find('.card');

      expect(cardDiv.classes()).toContain('card');
      expect(cardDiv.classes()).toContain('flex');
      expect(cardDiv.classes()).toContain('flex-col');
      expect(cardDiv.classes()).toContain('w-full');
      expect(cardDiv.classes()).toContain('h-full');
    });
  });

  describe('Data Display', () => {
    it('should display correct temperature format', () => {
      const wrapper = mount(WeatherWidget);
      const text = wrapper.text();

      expect(text).toMatch(/\d+°C/);
    });

    it('should display weather condition', () => {
      const wrapper = mount(WeatherWidget);
      const text = wrapper.text();

      expect(text).toContain('Wolkig');
    });

    it('should display city name', () => {
      const wrapper = mount(WeatherWidget);
      const text = wrapper.text();

      expect(text).toContain('Karlsruhe');
    });
  });

  describe('Visual Layout', () => {
    it('should apply flexbox layout classes', () => {
      const wrapper = mount(WeatherWidget);
      const card = wrapper.find('.card');

      expect(card.classes('flex')).toBe(true);
      expect(card.classes('flex-col')).toBe(true);
      expect(card.classes('justify-center')).toBe(true);
    });

    it('should apply full width and height classes', () => {
      const wrapper = mount(WeatherWidget);
      const card = wrapper.find('.card');

      expect(card.classes('w-full')).toBe(true);
      expect(card.classes('h-full')).toBe(true);
    });
  });

  describe('Component Lifecycle', () => {
    it('should mount without errors', () => {
      expect(() => {
        mount(WeatherWidget);
      }).not.toThrow();
    });

    it('should unmount without errors', () => {
      const wrapper = mount(WeatherWidget);
      expect(() => {
        wrapper.unmount();
      }).not.toThrow();
    });
  });
});

