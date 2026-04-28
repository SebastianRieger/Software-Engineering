/**
 * Test Suite Index and Overview
 * Central reference for all test files and their purposes
 */

/**
 * UNIT TESTS - COMPONENTS
 *
 * Location: src/tests/unit/components/
 *
 * Files:
 * - WeatherWidget.spec.ts
 *   Tests: rendering, data display, CSS classes, lifecycle
 *   Coverage: 80%+
 *
 * - ClockWidget.spec.ts
 *   Tests: rendering, time display, lifecycle
 *   Coverage: 75%+
 *
 * - TemplateWidget.spec.ts
 *   Tests: rendering, styling, component lifecycle
 *   Coverage: 70%+
 */

/**
 * UNIT TESTS - UTILITIES
 *
 * Location: src/tests/unit/utils/
 *
 * Files:
 * - formatters.spec.ts
 *   Functions tested:
 *   ✓ formatTemperature(celsius, decimals)
 *   ✓ formatHumidity(humidity)
 *   ✓ getWeatherClass(condition)
 *   ✓ isValidUrl(url)
 *   ✓ clamp(value, min, max)
 *   ✓ generateId(prefix)
 *   ✓ formatTime(date)
 *   ✓ formatDate(date)
 *   Coverage: 90%+
 */

/**
 * COMPOSABLE TESTS
 *
 * Location: src/tests/composables/
 *
 * Files:
 * - useEditMode.spec.ts
 *   Tests: edit mode toggle, keyboard handling, lifecycle
 *   Functions: toggleEditMode(), handleKeydown(), setupKeyboardListener()
 *   Coverage: 85%+
 *
 * - useModuleShop.spec.ts
 *   Tests: shop state, open/close, widget addition
 *   Functions: toggleShop(), openShop(), closeShop(), addWidget()
 *   Coverage: 85%+
 *
 * - useWidgetManager.spec.ts
 *   Tests: widget lifecycle, DOM operations, widget movement
 *   Functions: insertWidgetIntoCell(), clearCell(), moveWidgets()
 *   Coverage: 75%+
 */

/**
 * INTEGRATION TESTS
 *
 * Location: src/tests/integration/
 *
 * Files:
 * - state-management.spec.ts
 *   Tests: reactive state, store operations, computed values
 *   Tested concepts: widgets map, edit mode, cell selection
 *   Coverage: 80%+
 *
 * - composable-integration.spec.ts
 *   Tests: composable interactions, keyboard workflows
 *   Tested flows: edit mode + shop toggle, widget addition
 *   Coverage: 75%+
 */

/**
 * CONFIGURATION FILES
 *
 * Files:
 * - vitest.config.ts (root)
 *   Vitest configuration with coverage thresholds
 *
 * - setup.ts
 *   Global test setup (window.matchMedia mock, etc.)
 *
 * - test-utils.ts
 *   Common test utilities, fixtures, and test data
 */

/**
 * RUNNING TESTS - QUICK REFERENCE
 *
 * All tests:
 *   npm run test
 *
 * Watch mode:
 *   npm run test -- --watch
 *
 * UI dashboard:
 *   npm run test:ui
 *
 * Coverage report:
 *   npm run test:coverage
 *
 * Single file:
 *   npm run test -- WeatherWidget.spec.ts
 *
 * Specific pattern:
 *   npm run test -- --grep "formatTemperature"
 */

/**
 * TEST STATISTICS
 *
 * Component Tests:        15+ test cases
 * Composable Tests:       40+ test cases
 * Utility Tests:          50+ test cases
 * Integration Tests:      15+ test cases
 * ─────────────────────────────────────
 * Total:                  120+ test cases
 *
 * Target Coverage:        80%
 * Target Statements:      80%
 * Target Branches:        75%
 * Target Functions:       80%
 * Target Lines:           80%
 */

/**
 * TEST ORGANIZATION PRINCIPLES
 *
 * 1. Isolation
 *    - Each test is independent
 *    - beforeEach/afterEach for setup/cleanup
 *
 * 2. Clarity
 *    - Descriptive test names
 *    - Comments explain complex logic
 *    - Arrange-Act-Assert pattern
 *
 * 3. Coverage
 *    - Happy path scenarios
 *    - Edge cases
 *    - Error conditions
 *
 * 4. Maintainability
 *    - DRY principle applied
 *    - Helper functions in test-utils.ts
 *    - Consistent structure across files
 */

/**
 * BEST PRACTICES CHECKLIST
 *
 * ✓ All comments in English
 * ✓ Clean code formatting
 * ✓ No code duplication
 * ✓ Proper test isolation
 * ✓ Meaningful assertions
 * ✓ Comprehensive describe blocks
 * ✓ Mock usage where appropriate
 * ✓ No hardcoded test data
 * ✓ Proper async handling
 * ✓ DOM cleanup after tests
 */

export const TEST_SUITE_INFO = {
  version: '1.0.0',
  framework: 'Vitest 2.1.8',
  vueVersion: '3.5.22',
  totalTests: 120,
  coverageTarget: 80,
  lastUpdated: '2026-04-28',
};

