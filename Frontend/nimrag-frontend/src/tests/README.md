# Frontend Test Suite Documentation

## Overview

Comprehensive test suite for the Nimrag Smart Mirror Frontend using **Vitest** and **Vue Test Utils**. Tests cover component units, composables, utility functions, state management, and integration scenarios.

## Test Structure

```
src/tests/
├── setup.ts                           # Test environment configuration
├── unit/
│   ├── components/
│   │   ├── WeatherWidget.spec.ts     # Weather widget rendering tests
│   │   ├── ClockWidget.spec.ts       # Clock widget tests
│   │   └── TemplateWidget.spec.ts    # Template widget tests
│   └── utils/
│       └── formatters.spec.ts        # Utility function tests
├── composables/
│   ├── useEditMode.spec.ts           # Edit mode composable tests
│   ├── useModuleShop.spec.ts         # Module shop composable tests
│   └── useWidgetManager.spec.ts      # Widget manager composable tests
└── integration/
    ├── state-management.spec.ts      # State management integration tests
    └── composable-integration.spec.ts # Composable interaction tests
```

## Running Tests

### Install Dependencies

```bash
cd Frontend/nimrag-frontend
npm install
```

### Run All Tests

```bash
npm run test
```

### Run Tests in Watch Mode

```bash
npm run test -- --watch
```

### Run with UI

```bash
npm run test:ui
```

### Generate Coverage Report

```bash
npm run test:coverage
```

## Test Categories

### 1. Component Unit Tests

**Files:**
- `WeatherWidget.spec.ts` - Tests weather display component
- `ClockWidget.spec.ts` - Tests clock/time display
- `TemplateWidget.spec.ts` - Tests widget template

**Coverage:**
- Component rendering
- Props and data display
- CSS class application
- Lifecycle hooks (mount/unmount)
- Visual layout verification

### 2. Composable Tests

**Files:**
- `useEditMode.spec.ts` - Edit mode state and keyboard handling
- `useModuleShop.spec.ts` - Shop state and widget management
- `useWidgetManager.spec.ts` - Widget lifecycle and DOM manipulation

**Coverage:**
- State initialization
- State transitions
- Callback execution
- Event handling
- Independent state management

### 3. Utility Function Tests

**File:** `formatters.spec.ts`

**Functions Tested:**
- `formatTemperature()` - Temperature formatting
- `formatHumidity()` - Humidity percentage
- `getWeatherClass()` - Weather condition mapping
- `isValidUrl()` - URL validation
- `clamp()` - Number range clamping
- `generateId()` - Unique ID generation
- `formatTime()` - Time formatting (HH:MM:SS)
- `formatDate()` - Date formatting (DD.MM.YYYY)

### 4. Integration Tests

**Files:**
- `state-management.spec.ts` - Reactive state handling and store operations
- `composable-integration.spec.ts` - Composable interaction patterns

**Coverage:**
- State consistency
- Composable interactions
- Keyboard event workflows
- Widget addition flows
- Reactive computed values

## Test Statistics

| Category | Test Count | Target Coverage |
|----------|-----------|-----------------|
| Components | 15+ | 80% |
| Composables | 40+ | 85% |
| Utilities | 50+ | 90% |
| Integration | 15+ | 75% |
| **Total** | **120+** | **80%** |

## Key Features

### ✅ Clean Code Practices
- Descriptive test names
- Clear arrange-act-assert pattern
- Comprehensive comments in English
- Logical test organization
- Reduced code duplication

### ✅ Comprehensive Coverage
- Happy path scenarios
- Edge cases
- Error handling
- Integration flows
- State consistency

### ✅ Best Practices
- Isolation via `beforeEach` and `afterEach`
- Mock functions with Vitest
- No side effects in tests
- Reactive state validation
- DOM cleanup

## Example Test Patterns

### Component Testing
```typescript
it('should render weather widget correctly', () => {
  const wrapper = mount(WeatherWidget);
  expect(wrapper.find('.card').exists()).toBe(true);
  expect(wrapper.text()).toContain('21°C');
});
```

### Composable Testing
```typescript
it('should toggle edit mode', () => {
  const { isEditMode, toggleEditMode } = useEditMode();
  expect(isEditMode.value).toBe(false);
  toggleEditMode();
  expect(isEditMode.value).toBe(true);
});
```

### Utility Function Testing
```typescript
it('should format temperature', () => {
  expect(formatTemperature(20.5, 1)).toBe('20.5°C');
});
```

### Integration Testing
```typescript
it('should integrate edit mode with shop', () => {
  const editMode = useEditMode();
  const shop = useModuleShop();
  
  editMode.toggleEditMode();
  shop.toggleShop();
  
  expect(editMode.isEditMode.value).toBe(true);
  expect(shop.isShopOpen.value).toBe(true);
});
```

## Configuration Files

### vitest.config.ts
- Test environment: jsdom
- Global test utilities enabled
- Coverage thresholds defined
- Setup files configured

### Setup (src/tests/setup.ts)
- Window.matchMedia mock
- Console error suppression
- Test environment initialization

## CI/CD Integration

Tests are designed to run in:
- Local development (watch mode)
- CI/CD pipelines (GitHub Actions)
- Pre-commit hooks
- Pull request checks

## Coverage Targets

Target coverage thresholds (in vitest.config.ts):
- **Lines:** 80%
- **Functions:** 80%
- **Branches:** 75%
- **Statements:** 80%

## Debugging Tests

### Run Single Test File
```bash
npm run test -- WeatherWidget.spec.ts
```

### Run with Console Output
```bash
npm run test -- --reporter=verbose
```

### Debug in VSCode
1. Use Jest/Vitest extension
2. Set breakpoints in test files
3. Run debug configuration

## Adding New Tests

When adding new features:

1. **Create test file** in appropriate directory
2. **Follow naming convention**: `ComponentName.spec.ts`
3. **Use describe/it blocks** for organization
4. **Add English comments** for clarity
5. **Test happy path AND edge cases**
6. **Verify coverage** doesn't drop below 80%

## Common Issues

### Tests timeout
- Increase timeout in vitest.config.ts
- Check for unresolved async operations

### DOM errors
- Ensure mount points exist in beforeEach
- Use proper wrapper.unmount() in afterEach

### Reactive state issues
- Import from 'vue' for reactive/ref/computed
- Use .value to access ref/computed values

## Resources

- [Vitest Documentation](https://vitest.dev)
- [Vue Test Utils Guide](https://test-utils.vuejs.org)
- [Testing Library Best Practices](https://testing-library.com/docs)

## Maintenance

Review and update tests when:
- Components are refactored
- Composables change behavior
- Utility functions are modified
- New features are added
- Bugs are discovered and fixed

---

**Last Updated:** 2026-04-28  
**Test Framework:** Vitest 2.1.8  
**Vue:** 3.5.22

