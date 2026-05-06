const fs = require('node:fs')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')
const reportsRoot = path.join(repoRoot, 'reports', 'quality')
const summaryPath = path.join(reportsRoot, 'summary.json')
const thresholdsPath = path.join(__dirname, 'quality_thresholds.json')

function readJson(filePath, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'))
  } catch {
    return fallback
  }
}

function getStep(summarySection, stepLabel) {
  return summarySection?.status?.steps?.find((step) => step.label === stepLabel) ?? null
}

function formatNumber(value) {
  return typeof value === 'number' ? value.toFixed(2) : 'n/a'
}

const summary = readJson(summaryPath)
const thresholds = readJson(thresholdsPath, {})
const gates = thresholds?.gates?.phase2 ?? null

if (!summary) {
  console.error(`Missing quality summary: ${path.relative(repoRoot, summaryPath)}`)
  process.exit(1)
}

if (!gates?.enabled) {
  console.log('Phase 2 quality gates are disabled. Skipping gate enforcement.')
  process.exit(0)
}

const failures = []

for (const stepLabel of gates.requiredSteps?.backend ?? []) {
  const step = getStep(summary.backend, stepLabel)
  if (!step?.success) {
    failures.push(`Backend step failed: ${stepLabel}`)
  }
}

for (const stepLabel of gates.requiredSteps?.frontend ?? []) {
  const step = getStep(summary.frontend, stepLabel)
  if (!step?.success) {
    failures.push(`Frontend step failed: ${stepLabel}`)
  }
}

for (const stepLabel of gates.requiredSteps?.duplication ?? []) {
  const step = getStep(summary.duplication, stepLabel)
  if (!step?.success) {
    failures.push(`Duplication step failed: ${stepLabel}`)
  }
}

const backendCoverageMin = gates.coverage?.backend?.linesMin
if (typeof backendCoverageMin === 'number') {
  const backendCoverage = summary.backend?.coverage?.linesPct
  if (typeof backendCoverage !== 'number' || backendCoverage < backendCoverageMin) {
    failures.push(
      `Backend line coverage ${formatNumber(backendCoverage)}% is below ${backendCoverageMin}%`,
    )
  }
}

const frontendCoverageMin = gates.coverage?.frontend?.linesMin
if (typeof frontendCoverageMin === 'number') {
  const frontendCoverage = summary.frontend?.coverage?.linesPct
  if (typeof frontendCoverage !== 'number' || frontendCoverage < frontendCoverageMin) {
    failures.push(
      `Frontend line coverage ${formatNumber(frontendCoverage)}% is below ${frontendCoverageMin}%`,
    )
  }
}

const duplicationMax = gates.duplication?.maxPercent
if (typeof duplicationMax === 'number') {
  const duplicationPct = summary.duplication?.metrics?.percentage
  if (typeof duplicationPct !== 'number' || duplicationPct > duplicationMax) {
    failures.push(
      `Duplication ${formatNumber(duplicationPct)}% exceeds ${duplicationMax}%`,
    )
  }
}

const maxFrontendEslintErrors = gates.eslint?.maxErrors
if (typeof maxFrontendEslintErrors === 'number') {
  const eslintErrors = summary.frontend?.lint?.errors
  if (typeof eslintErrors !== 'number' || eslintErrors > maxFrontendEslintErrors) {
    failures.push(
      `Frontend ESLint errors ${eslintErrors ?? 'n/a'} exceed ${maxFrontendEslintErrors}`,
    )
  }
}

if (failures.length > 0) {
  console.error('Quality gates failed:')
  for (const failure of failures) {
    console.error(`- ${failure}`)
  }
  process.exit(1)
}

console.log('Quality gates passed:')
console.log(`- Backend coverage: ${formatNumber(summary.backend?.coverage?.linesPct)}%`)
console.log(`- Frontend ESLint errors: ${summary.frontend?.lint?.errors ?? 'n/a'}`)
console.log(`- Duplication: ${formatNumber(summary.duplication?.metrics?.percentage)}%`)