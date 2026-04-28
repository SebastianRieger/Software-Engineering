import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';
import tailwindcss from '@tailwindcss/vite';

/**
 * Vitest Configuration for Nimrag Smart Mirror Frontend
 * Configured for unit and integration testing of Vue 3 components and composables
 */
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    // Use jsdom environment for DOM testing
    environment: 'jsdom',
    // Enable globals (describe, it, expect, etc.)
    globals: true,
    // Test file patterns
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/**/*.d.ts',
        '**/*.config.ts',
        '**/mockData',
      ],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 75,
        statements: 80,
      },
    },
    // Setup files
    setupFiles: ['src/tests/setup.ts'],
  },
});

