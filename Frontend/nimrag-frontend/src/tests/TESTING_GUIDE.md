# Test Execution Guide

## Quick Start

### 1. Install Dependencies
```bash
cd Frontend/nimrag-frontend
npm install
```

### 2. Run All Tests
```bash
npm run test
```

### 3. View Coverage
```bash
npm run test:coverage
```

---

## Detailed Testing Workflow

### Step 1: Setup Test Environment

Ensure all dependencies are installed:
```bash
npm install
```

Check configuration:
```bash
cat vitest.config.ts
```

### Step 2: Run Tests by Category

**All Tests**
```bash
npm run test
```

**Watch Mode (Recommended for Development)**
```bash
npm run test -- --watch
```

**UI Dashboard (Visual Test Runner)**
```bash
npm run test:ui
```

**With Coverage Report**
```bash
npm run test:coverage
```

### Step 3: Run Specific Test Suites

**Component Tests Only**
```bash
npm run test -- src/tests/unit/components/
```

**Composable Tests Only**
```bash
npm run test -- src/tests/composables/
```

**Utility Tests Only**
```bash
npm run test -- src/tests/unit/utils/
```

**Integration Tests Only**
```bash
npm run test -- src/tests/integration/
```

### Step 4: Run Individual Test Files

**WeatherWidget Tests**
```bash
npm run test -- WeatherWidget.spec.ts
```

**Utility Functions Tests**
```bash
npm run test -- formatters.spec.ts
```

**useEditMode Tests**
```bash
npm run test -- useEditMode.spec.ts
```

### Step 5: Filter Tests by Name

**Run tests matching pattern**
```bash
npm run test -- --grep "formatTemperature"
```

**Run tests with specific keyword**
```bash
npm run test -- --grep "toggle"
```

---

## Interpreting Test Output

### Success Output Example
```
✓ src/tests/unit/components/WeatherWidget.spec.ts (8)
✓ src/tests/composables/useEditMode.spec.ts (25)
✓ src/tests/unit/utils/formatters.spec.ts (40)

Test Files  3 passed (3)
     Tests  120 passed (120)
  Seconds  2.45s
```

### Coverage Report
```
File                    | % Stmts | % Branch | % Funcs | % Lines |
WeatherWidget.vue       |    100  |   95     |   100   |   100   |
useEditMode.ts          |     95  |   92     |   95    |    95   |
formatters.ts           |     98  |   96     |   98    |    98   |
─────────────────────────────────────────────────────────────────
All files               |     80  |   75     |   80    |    80   |
```

---

## Common Commands Reference

```bash
# Run all tests
npm run test

# Run tests and watch for changes
npm run test -- --watch

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage

# Run tests with reporter
npm run test -- --reporter=verbose

# Run specific test file
npm run test -- WeatherWidget.spec.ts

# Run tests matching pattern
npm run test -- --grep "toggle"

# Run tests excluding pattern
npm run test -- --grep "!slow"

# Run single test
npm run test -- Weather.spec.ts -t "should render"

# Show help
npm run test -- --help
```

---

## Debugging Tests

### Debug in VSCode

1. Add breakpoint to test file
2. Run with debugger:
```bash
node --inspect-brk ./node_modules/vitest/vitest.mjs run WeatherWidget.spec.ts
```
3. Open `chrome://inspect` in Chrome

### Debug in Browser

```bash
npm run test:ui
```

Then open the UI at http://localhost:51204

### Verbose Output

```bash
npm run test -- --reporter=verbose
```

---

## Pre-commit Hook Setup

Ensure tests pass before commit:

```bash
# Install pre-commit
npm install husky lint-staged --save-dev

# Initialize husky
npx husky install

# Create pre-commit hook
npx husky add .husky/pre-commit "npm run test"
```

---

## CI/CD Integration

### GitHub Actions

Tests automatically run on:
- Push to any branch
- Pull requests
- Scheduled daily checks

### Manual Trigger

```bash
# Run tests locally before pushing
npm run test

# Check coverage meets targets
npm run test:coverage

# Fix any linting issues
npm run lint
```

---

## Troubleshooting

### Tests Not Found
```bash
# Verify file exists and has .spec.ts extension
ls -la src/tests/unit/components/
```

### Timeout Errors
```bash
# Increase timeout
npm run test -- --testTimeout=10000
```

### DOM Errors
```bash
# Check setup.ts is loaded
cat src/tests/setup.ts
```

### Port Already in Use (UI)
```bash
# Use different port
npm run test:ui -- --port=5174
```

---

## Performance Tips

### Run Tests in Parallel
```bash
npm run test -- --threads
```

### Run Only Changed Tests
```bash
npm run test -- --changed
```

### Skip Type Checking
```bash
npm run test -- --no-typecheck
```

---

## Coverage Target Checklist

Before committing, verify:

- [ ] All tests pass locally
- [ ] Coverage >= 80% statements
- [ ] Coverage >= 75% branches
- [ ] Coverage >= 80% functions
- [ ] Coverage >= 80% lines
- [ ] No console errors/warnings
- [ ] No failing tests
- [ ] No skipped tests (except deliberately)

---

## Test Metrics Dashboard

View current metrics:
```bash
npm run test:coverage
# Open htmlcov/index.html in browser
```

---

## Continuous Integration

### Local Pre-push Check
```bash
#!/bin/bash
# Check all tests pass
npm run test || exit 1
# Check coverage
npm run test:coverage || exit 1
echo "✅ All tests passed!"
```

---

## Weekly Maintenance

1. **Update Dependencies**
   ```bash
   npm update
   ```

2. **Run Full Test Suite**
   ```bash
   npm run test
   ```

3. **Check Coverage Trends**
   ```bash
   npm run test:coverage
   ```

4. **Review Test Results**
   - Check for flaky tests
   - Update outdated test data
   - Refactor slow tests

---

**Last Updated:** 2026-04-28

