/**
 * Utility functions for Nimrag Smart Mirror Frontend
 * Contains helper functions for formatting and validation
 */

export function formatTemperature(celsius: number, decimals: number = 0): string {
  return `${celsius.toFixed(decimals)}°C`;
}

export function formatHumidity(humidity: number): string {
  return `${Math.round(humidity)}%`;
}

export function getWeatherClass(condition: string): string {
  const lower = condition.toLowerCase();
  if (lower.includes('cloudy') || lower.includes('wolkig')) return 'weather-cloudy';
  if (lower.includes('rain') || lower.includes('regen')) return 'weather-rainy';
  if (lower.includes('sunny') || lower.includes('sonnig')) return 'weather-sunny';
  return 'weather-unknown';
}

export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function generateId(prefix: string = 'id'): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function formatTime(date: Date = new Date()): string {
  const h = String(date.getHours()).padStart(2, '0');
  const m = String(date.getMinutes()).padStart(2, '0');
  const s = String(date.getSeconds()).padStart(2, '0');
  return `${h}:${m}:${s}`;
}

export function formatDate(date: Date = new Date()): string {
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  return `${day}.${month}.${year}`;
}

