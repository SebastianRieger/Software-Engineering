/**
 * formatters.spec.ts
 * Unit tests for utility formatter functions
 * Tests formatting, validation, and helper functions
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  formatTemperature,
  formatHumidity,
  getWeatherClass,
  isValidUrl,
  clamp,
  generateId,
  formatTime,
  formatDate,
} from '@/utils/formatters';

describe('Utility Formatter Functions', () => {
  describe('formatTemperature', () => {
    it('should format temperature with default decimal places', () => {
      expect(formatTemperature(20)).toBe('20°C');
      expect(formatTemperature(25.5)).toBe('26°C');
    });

    it('should format temperature with custom decimal places', () => {
      expect(formatTemperature(20.567, 1)).toBe('20.6°C');
      expect(formatTemperature(20.567, 2)).toBe('20.57°C');
    });

    it('should handle negative temperatures', () => {
      expect(formatTemperature(-5)).toBe('-5°C');
      expect(formatTemperature(-15.8, 1)).toBe('-15.8°C');
    });

    it('should handle zero temperature', () => {
      expect(formatTemperature(0)).toBe('0°C');
    });

    it('should handle large temperatures', () => {
      expect(formatTemperature(999)).toBe('999°C');
    });
  });

  describe('formatHumidity', () => {
    it('should format humidity as percentage', () => {
      expect(formatHumidity(50)).toBe('50%');
      expect(formatHumidity(100)).toBe('100%');
    });

    it('should round humidity values', () => {
      expect(formatHumidity(50.4)).toBe('50%');
      expect(formatHumidity(50.6)).toBe('51%');
    });

    it('should handle zero humidity', () => {
      expect(formatHumidity(0)).toBe('0%');
    });

    it('should handle decimal humidity values', () => {
      expect(formatHumidity(65.7)).toBe('66%');
      expect(formatHumidity(45.3)).toBe('45%');
    });
  });

  describe('getWeatherClass', () => {
    it('should return cloudy class for cloudy conditions', () => {
      expect(getWeatherClass('cloudy')).toBe('weather-cloudy');
      expect(getWeatherClass('Cloudy')).toBe('weather-cloudy');
      expect(getWeatherClass('CLOUDY')).toBe('weather-cloudy');
    });

    it('should handle German weather conditions', () => {
      expect(getWeatherClass('wolkig')).toBe('weather-cloudy');
      expect(getWeatherClass('Wolkig')).toBe('weather-cloudy');
    });

    it('should return rainy class for rainy conditions', () => {
      expect(getWeatherClass('rain')).toBe('weather-rainy');
      expect(getWeatherClass('raining')).toBe('weather-rainy');
    });

    it('should handle German rain conditions', () => {
      expect(getWeatherClass('regen')).toBe('weather-rainy');
      expect(getWeatherClass('Regen')).toBe('weather-rainy');
    });

    it('should return sunny class for sunny conditions', () => {
      expect(getWeatherClass('sunny')).toBe('weather-sunny');
      expect(getWeatherClass('Sunny')).toBe('weather-sunny');
    });

    it('should handle German sunny conditions', () => {
      expect(getWeatherClass('sonnig')).toBe('weather-sunny');
      expect(getWeatherClass('Sonnig')).toBe('weather-sunny');
    });

    it('should return unknown for unrecognized conditions', () => {
      expect(getWeatherClass('unknown')).toBe('weather-unknown');
      expect(getWeatherClass('fog')).toBe('weather-unknown');
      expect(getWeatherClass('')).toBe('weather-unknown');
    });
  });

  describe('isValidUrl', () => {
    it('should validate correct HTTP URLs', () => {
      expect(isValidUrl('http://example.com')).toBe(true);
      expect(isValidUrl('http://localhost:3000')).toBe(true);
    });

    it('should validate correct HTTPS URLs', () => {
      expect(isValidUrl('https://example.com')).toBe(true);
      expect(isValidUrl('https://api.weather.com/v1')).toBe(true);
    });

    it('should reject invalid URLs', () => {
      expect(isValidUrl('not a url')).toBe(false);
      expect(isValidUrl('example.com')).toBe(false);
      expect(isValidUrl('')).toBe(false);
    });

    it('should validate URLs with paths and query params', () => {
      expect(isValidUrl('https://api.com/path?query=value')).toBe(true);
      expect(isValidUrl('https://example.com/path/to/resource')).toBe(true);
    });
  });

  describe('clamp', () => {
    it('should return value if within range', () => {
      expect(clamp(50, 0, 100)).toBe(50);
      expect(clamp(0, 0, 100)).toBe(0);
      expect(clamp(100, 0, 100)).toBe(100);
    });

    it('should clamp value to minimum', () => {
      expect(clamp(-10, 0, 100)).toBe(0);
      expect(clamp(-999, -50, 50)).toBe(-50);
    });

    it('should clamp value to maximum', () => {
      expect(clamp(150, 0, 100)).toBe(100);
      expect(clamp(999, -50, 50)).toBe(50);
    });

    it('should handle negative ranges', () => {
      expect(clamp(-75, -100, -50)).toBe(-75);
      expect(clamp(-120, -100, -50)).toBe(-100);
    });

    it('should handle decimal values', () => {
      expect(clamp(50.5, 0, 100)).toBe(50.5);
      expect(clamp(100.1, 0, 100)).toBe(100);
    });
  });

  describe('generateId', () => {
    it('should generate unique IDs', () => {
      const id1 = generateId();
      const id2 = generateId();

      expect(id1).not.toBe(id2);
    });

    it('should include default prefix', () => {
      const id = generateId();

      expect(id).toMatch(/^id_/);
    });

    it('should include custom prefix', () => {
      const id = generateId('widget');

      expect(id).toMatch(/^widget_/);
    });

    it('should include timestamp', () => {
      const id = generateId();
      const parts = id.split('_');

      expect(parts.length).toBe(3);
      expect(!isNaN(Number(parts[1]))).toBe(true);
    });

    it('should generate IDs with different prefixes', () => {
      const id1 = generateId('weather');
      const id2 = generateId('clock');

      expect(id1).toMatch(/^weather_/);
      expect(id2).toMatch(/^clock_/);
    });
  });

  describe('formatTime', () => {
    it('should format time correctly', () => {
      const date = new Date(2024, 0, 1, 14, 30, 45);
      expect(formatTime(date)).toBe('14:30:45');
    });

    it('should pad single digit hours with zero', () => {
      const date = new Date(2024, 0, 1, 9, 0, 0);
      expect(formatTime(date)).toBe('09:00:00');
    });

    it('should pad single digit minutes with zero', () => {
      const date = new Date(2024, 0, 1, 14, 5, 0);
      expect(formatTime(date)).toBe('14:05:00');
    });

    it('should pad single digit seconds with zero', () => {
      const date = new Date(2024, 0, 1, 14, 30, 3);
      expect(formatTime(date)).toBe('14:30:03');
    });

    it('should use current time if no date provided', () => {
      const result = formatTime();

      expect(result).toMatch(/\d{2}:\d{2}:\d{2}/);
    });

    it('should handle midnight', () => {
      const date = new Date(2024, 0, 1, 0, 0, 0);
      expect(formatTime(date)).toBe('00:00:00');
    });

    it('should handle times close to midnight', () => {
      const date = new Date(2024, 0, 1, 23, 59, 59);
      expect(formatTime(date)).toBe('23:59:59');
    });
  });

  describe('formatDate', () => {
    it('should format date in DD.MM.YYYY format', () => {
      const date = new Date(2024, 0, 15);
      expect(formatDate(date)).toBe('15.01.2024');
    });

    it('should pad single digit days with zero', () => {
      const date = new Date(2024, 0, 5);
      expect(formatDate(date)).toBe('05.01.2024');
    });

    it('should pad single digit months with zero', () => {
      const date = new Date(2024, 2, 15);
      expect(formatDate(date)).toBe('15.03.2024');
    });

    it('should format last day of year correctly', () => {
      const date = new Date(2024, 11, 31);
      expect(formatDate(date)).toBe('31.12.2024');
    });

    it('should format first day of year correctly', () => {
      const date = new Date(2024, 0, 1);
      expect(formatDate(date)).toBe('01.01.2024');
    });

    it('should use current date if no date provided', () => {
      const result = formatDate();

      expect(result).toMatch(/\d{2}\.\d{2}\.\d{4}/);
    });

    it('should handle different years', () => {
      const date2000 = new Date(2000, 0, 1);
      const date2025 = new Date(2025, 11, 31);

      expect(formatDate(date2000)).toContain('2000');
      expect(formatDate(date2025)).toContain('2025');
    });
  });

  describe('Integration', () => {
    it('should work together for weather display', () => {
      const temp = formatTemperature(21.5, 1);
      const humidity = formatHumidity(65);
      const weatherClass = getWeatherClass('wolkig');

      expect(temp).toBe('21.5°C');
      expect(humidity).toBe('65%');
      expect(weatherClass).toBe('weather-cloudy');
    });

    it('should work together for timestamp display', () => {
      const date = new Date(2024, 0, 15, 14, 30, 45);
      const time = formatTime(date);
      const dateStr = formatDate(date);

      expect(time).toBe('14:30:45');
      expect(dateStr).toBe('15.01.2024');
    });
  });
});

