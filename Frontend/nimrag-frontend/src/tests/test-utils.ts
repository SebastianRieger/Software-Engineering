/**
 * Test Utilities and Helpers
 * Common functions and fixtures used across test suites
 */

import { vi } from 'vitest';

/**
 * Mock component factory for testing
 */
export function createMockComponent(name: string = 'MockComponent', props: any = {}) {
  return {
    name,
    props,
    template: `<div class="mock-component">${name}</div>`,
  };
}

/**
 * Mock Vue app factory for testing widget mounting
 */
export function createMockApp() {
  return {
    mount: vi.fn(),
    unmount: vi.fn(),
    use: vi.fn(),
  };
}

/**
 * Create mock keyboard event
 */
export function createKeyboardEvent(key: string, type: string = 'keydown'): KeyboardEvent {
  return new KeyboardEvent(type, {
    key,
    bubbles: true,
    cancelable: true,
  });
}

/**
 * Mock fetch response
 */
export function createMockFetchResponse(data: any, ok: boolean = true) {
  return Promise.resolve({
    ok,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as Response);
}

/**
 * Setup DOM fixtures for component testing
 */
export function setupDOMFixtures() {
  // Create sample cell mount points
  for (let i = 1; i <= 12; i++) {
    const mount = document.createElement('div');
    mount.id = `cell-content-${i}`;
    mount.className = 'cell-mount';
    document.body.appendChild(mount);
  }
}

/**
 * Clean up DOM fixtures
 */
export function cleanupDOMFixtures() {
  const cells = document.querySelectorAll('.cell-mount');
  cells.forEach((cell) => cell.remove());
}

/**
 * Get all mounted cells
 */
export function getMountedCells(): HTMLElement[] {
  return Array.from(document.querySelectorAll('[id^="cell-content-"]'));
}

/**
 * Wait for async operations to complete
 */
export async function waitForAsync(ms: number = 0): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Test data constants
 */
export const TEST_DATA = {
  weatherWidget: {
    temp: '21°C',
    city: 'Karlsruhe',
    condition: 'wolkig',
  },
  validUrls: [
    'https://example.com',
    'http://localhost:3000',
    'https://api.weather.com/v1',
  ],
  invalidUrls: ['not-a-url', 'example.com', 'ftp://invalid.com'],
  temperatures: [-10, 0, 10, 20, 25.5, 30],
  humidityValues: [0, 25, 50, 75, 100],
  weatherConditions: ['sunny', 'cloudy', 'rainy', 'wolkig', 'regen'],
};

