const fs = require('node:fs')
const path = require('node:path')

const repoRoot = path.resolve(__dirname, '..')
const reportsRoot = path.join(repoRoot, 'reports', 'quality')
const thresholdsPath = path.join(__dirname, 'quality_thresholds.json')

function extractXmlAttr(tag, attrName) {
  const match = tag.match(new RegExp(`${attrName}="([^"]+)"`))
  return match ? Number(match[1]) : 0
}

function fileExists(filePath) {
  return fs.existsSync(filePath)
}

function readText(filePath) {
  return fs.readFileSync(filePath, 'utf8')
}

function readJson(filePath, fallback = null) {
  if (!fileExists(filePath)) {
    return fallback
  }
  try {
    return JSON.parse(readText(filePath))
  } catch {
    return fallback
  }
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true })
}

function writeText(filePath, content) {
  ensureDir(path.dirname(filePath))
  fs.writeFileSync(filePath, `${content}\n`, 'utf8')
}

function readStatus(section) {
  return readJson(path.join(reportsRoot, section, 'status.json'), {
    mode: section,
    success: false,
    steps: [],
    error: 'Missing status file',
  })
}

function parseJUnitCounts(filePath) {
  if (!fileExists(filePath)) {
    return null
  }

  const xml = readText(filePath)
  const rootMatch = xml.match(/<testsuites\b([^>]*)>/)
  if (rootMatch) {
    const rootTotals = {
      total: extractXmlAttr(rootMatch[1], 'tests'),
      failed: extractXmlAttr(rootMatch[1], 'failures'),
      errors: extractXmlAttr(rootMatch[1], 'errors'),
      skipped: extractXmlAttr(rootMatch[1], 'skipped'),
    }
    if (rootTotals.total > 0 || rootTotals.failed > 0 || rootTotals.errors > 0 || rootTotals.skipped > 0) {
      return rootTotals
    }
  }

  const matches = [...xml.matchAll(/<testsuite\b([^>]*)>/g)]
  if (matches.length === 0) {
    return null
  }

  return matches.reduce((totals, match) => {
    const tag = match[1] || ''
    return {
      total: totals.total + extractXmlAttr(tag, 'tests'),
      failed: totals.failed + extractXmlAttr(tag, 'failures'),
      errors: totals.errors + extractXmlAttr(tag, 'errors'),
      skipped: totals.skipped + extractXmlAttr(tag, 'skipped'),
    }
  }, { total: 0, failed: 0, errors: 0, skipped: 0 })
}

function calculatePct(covered, total) {
  if (typeof covered !== 'number' || typeof total !== 'number') {
    return null
  }

  if (total === 0) {
    return 100
  }

  return (covered / total) * 100
}

function relativePathFromRepo(filePath) {
  if (!filePath) {
    return filePath
  }

  return path.relative(repoRoot, filePath).split(path.sep).join('/')
}

function summarizeCoverageJson(filePath) {
  const payload = readJson(filePath)
  if (!payload || !payload.totals) {
    return null
  }

  const totals = payload.totals
  const branchesMeasured = payload.meta?.branch_coverage === true || typeof totals.num_branches === 'number'

  return {
    linesPct: calculatePct(totals.covered_lines, totals.num_statements),
    coveredLines: totals.covered_lines,
    statements: totals.num_statements,
    missingLines: totals.missing_lines,
    branchesMeasured,
    branchesPct: branchesMeasured ? calculatePct(totals.covered_branches ?? 0, totals.num_branches ?? 0) : null,
    coveredBranches: branchesMeasured ? (totals.covered_branches ?? 0) : null,
    branches: branchesMeasured ? (totals.num_branches ?? 0) : null,
    missingBranches: branchesMeasured ? (totals.missing_branches ?? 0) : null,
    partialBranches: branchesMeasured ? (totals.num_partial_branches ?? 0) : null,
  }
}

function summarizeVitestCoverage() {
  const summaryPath = path.join(reportsRoot, 'frontend', 'coverage', 'coverage-summary.json')
  const summary = readJson(summaryPath)
  if (!summary || !summary.total) {
    return null
  }

  return {
    linesPct: summary.total.lines?.pct ?? null,
    statementsPct: summary.total.statements?.pct ?? null,
    functionsPct: summary.total.functions?.pct ?? null,
    branchesPct: summary.total.branches?.pct ?? null,
  }
}

function summarizeVitestResults() {
  const payload = readJson(path.join(reportsRoot, 'frontend', 'vitest.json'))
  if (!payload) {
    return null
  }

  return {
    total: payload.numTotalTests ?? null,
    passed: payload.numPassedTests ?? null,
    failed: payload.numFailedTests ?? null,
    skipped: payload.numPendingTests ?? payload.numTodoTests ?? 0,
    success: payload.success ?? false,
  }
}

function summarizeEslint() {
  const results = readJson(path.join(reportsRoot, 'frontend', 'eslint.json'), [])
  if (!Array.isArray(results)) {
    return null
  }

  let errors = 0
  let warnings = 0
  const fileHotspots = []

  for (const result of results) {
    errors += result.errorCount || 0
    warnings += result.warningCount || 0
    if ((result.errorCount || 0) > 0 || (result.warningCount || 0) > 0) {
      fileHotspots.push({
        file: relativePathFromRepo(result.filePath),
        errors: result.errorCount || 0,
        warnings: result.warningCount || 0,
      })
    }
  }

  fileHotspots.sort((left, right) => (right.errors + right.warnings) - (left.errors + left.warnings))

  return {
    errors,
    warnings,
    filesWithFindings: fileHotspots.length,
    topFiles: fileHotspots.slice(0, 5),
  }
}

function summarizeBackendFlake8() {
  const flake8Path = path.join(reportsRoot, 'backend', 'flake8.txt')
  if (!fileExists(flake8Path)) {
    return null
  }

  const text = readText(flake8Path).trim()
  if (!text) {
    return {
      findings: 0,
      filesWithFindings: 0,
      topCodes: [],
      categoryCounts: {},
      topFiles: [],
    }
  }

  const codeCounts = new Map()
  const categoryCounts = new Map()
  const fileCounts = new Map()
  let findings = 0

  for (const line of text.split(/\r?\n/)) {
    const match = line.match(/^(.*?):(\d+):(\d+):\s*([A-Z]+\d+)\s+(.*)$/)
    if (!match) {
      continue
    }

    const file = relativePathFromRepo(match[1])
    const code = match[4]
    const category = (code.match(/^[A-Z]+/) || [code])[0]

    findings += 1
    codeCounts.set(code, (codeCounts.get(code) || 0) + 1)
    categoryCounts.set(category, (categoryCounts.get(category) || 0) + 1)
    fileCounts.set(file, (fileCounts.get(file) || 0) + 1)
  }

  const topCodes = [...codeCounts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .slice(0, 5)
    .map(([code, count]) => ({ code, count }))

  const topFiles = [...fileCounts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .slice(0, 5)
    .map(([file, count]) => ({ file, count }))

  return {
    findings,
    filesWithFindings: fileCounts.size,
    topCodes,
    categoryCounts: Object.fromEntries([...categoryCounts.entries()].sort((left, right) => left[0].localeCompare(right[0]))),
    topFiles,
  }
}

function parseRadonCc() {
  const payload = readJson(path.join(reportsRoot, 'backend', 'radon-cc.json'), {})
  const hotspots = []
  for (const [file, entries] of Object.entries(payload || {})) {
    if (!Array.isArray(entries)) {
      continue
    }
    for (const entry of entries) {
      hotspots.push({
        file,
        name: entry.name,
        complexity: entry.complexity,
        rank: entry.rank,
        type: entry.type,
        lineno: entry.lineno,
      })
    }
  }
  hotspots.sort((left, right) => (right.complexity || 0) - (left.complexity || 0))
  return hotspots
}

function parseRadonMi() {
  const payload = readJson(path.join(reportsRoot, 'backend', 'radon-mi.json'), {})
  const results = []
  for (const [file, value] of Object.entries(payload || {})) {
    if (typeof value === 'number') {
      results.push({ file, mi: value })
      continue
    }
    if (value && typeof value === 'object') {
      results.push({
        file,
        mi: value.mi ?? value.value ?? null,
        rank: value.rank ?? null,
      })
    }
  }
  results.sort((left, right) => (left.mi ?? Infinity) - (right.mi ?? Infinity))
  return results
}

function parseRadonHal() {
  const payload = readJson(path.join(reportsRoot, 'backend', 'radon-hal.json'), {})
  const results = []
  for (const [file, value] of Object.entries(payload || {})) {
    if (value && typeof value === 'object') {
      const totals = value.total || value
      results.push({
        file,
        volume: totals.volume ?? null,
        difficulty: totals.difficulty ?? null,
        effort: totals.effort ?? null,
      })
    }
  }
  results.sort((left, right) => (right.volume ?? 0) - (left.volume ?? 0))
  return results
}

function parseRadonRaw() {
  return readJson(path.join(reportsRoot, 'backend', 'radon-raw.json'), {})
}

function summarizeBackendCc(entries) {
  const rankDistribution = {}
  const typeDistribution = {}
  const fileStats = new Map()
  let highRiskEntries = 0

  for (const entry of entries) {
    if (entry.rank) {
      rankDistribution[entry.rank] = (rankDistribution[entry.rank] || 0) + 1
    }

    if (entry.type) {
      typeDistribution[entry.type] = (typeDistribution[entry.type] || 0) + 1
    }

    const stats = fileStats.get(entry.file) || {
      file: entry.file,
      entries: 0,
      totalComplexity: 0,
      highestComplexity: 0,
      highRiskEntries: 0,
    }

    const complexity = entry.complexity || 0
    stats.entries += 1
    stats.totalComplexity += complexity
    stats.highestComplexity = Math.max(stats.highestComplexity, complexity)
    if (complexity >= 11) {
      stats.highRiskEntries += 1
      highRiskEntries += 1
    }

    fileStats.set(entry.file, stats)
  }

  const topFiles = [...fileStats.values()]
    .sort((left, right) => {
      return (right.highRiskEntries - left.highRiskEntries)
        || (right.highestComplexity - left.highestComplexity)
        || (right.totalComplexity - left.totalComplexity)
        || left.file.localeCompare(right.file)
    })
    .slice(0, 5)

  return {
    highRiskEntries,
    rankDistribution,
    typeDistribution,
    topFiles,
  }
}

function summarizeBackendMi(entries) {
  const rankDistribution = {}
  const bands = {
    under20: 0,
    under40: 0,
    under60: 0,
    atLeast60: 0,
  }

  for (const entry of entries) {
    if (entry.rank) {
      rankDistribution[entry.rank] = (rankDistribution[entry.rank] || 0) + 1
    }

    const mi = entry.mi
    if (typeof mi !== 'number') {
      continue
    }

    if (mi < 20) {
      bands.under20 += 1
    } else if (mi < 40) {
      bands.under40 += 1
    } else if (mi < 60) {
      bands.under60 += 1
    } else {
      bands.atLeast60 += 1
    }
  }

  return {
    rankDistribution,
    bands,
  }
}

function summarizeBackendRawMetrics(rawMetrics) {
  const files = Object.entries(rawMetrics || {}).map(([file, metrics]) => ({
    file,
    loc: metrics?.loc ?? 0,
    lloc: metrics?.lloc ?? 0,
    sloc: metrics?.sloc ?? 0,
    comments: metrics?.comments ?? 0,
    blank: metrics?.blank ?? 0,
  }))

  files.sort((left, right) => {
    return (right.sloc - left.sloc)
      || (right.lloc - left.lloc)
      || (right.loc - left.loc)
      || left.file.localeCompare(right.file)
  })

  return {
    totalFiles: files.length,
    totalLoc: files.reduce((total, file) => total + file.loc, 0),
    totalSloc: files.reduce((total, file) => total + file.sloc, 0),
    largestFiles: files.slice(0, 5),
  }
}

function summarizeDuplication() {
  const candidateFiles = [
    path.join(reportsRoot, 'shared', 'jscpd', 'jscpd-report.json'),
    path.join(reportsRoot, 'shared', 'jscpd', 'report.json'),
  ]
  const payload = candidateFiles.map((candidate) => readJson(candidate)).find(Boolean)
  if (!payload) {
    return null
  }

  const total = payload.statistics?.total || payload.total || {}
  const duplicates = payload.duplicates || []

  return {
    percentage: total.percentage ?? total.duplicatedPercentage ?? null,
    duplicatedLines: total.duplicatedLines ?? null,
    totalLines: total.lines ?? null,
    clones: Array.isArray(duplicates) ? duplicates.length : 0,
  }
}

function summarizeGestureConfusions(failures) {
  if (!Array.isArray(failures)) {
    return []
  }

  const counts = new Map()

  for (const failure of failures) {
    const expected = failure?.label ?? 'unknown'
    const detected = failure?.detected_gesture ?? 'not_detected'
    const key = `${expected}=>${detected}`
    const current = counts.get(key) ?? { expected, detected, count: 0 }
    current.count += 1
    counts.set(key, current)
  }

  return [...counts.values()]
    .sort((left, right) => right.count - left.count || left.expected.localeCompare(right.expected))
    .slice(0, 5)
}

function summarizeNegativeSwipeSummary(summary) {
  if (!summary || typeof summary !== 'object') {
    return null
  }

  const topOffenders = Object.entries(summary)
    .map(([label, value]) => ({
      label,
      videoFalsePositiveRate: value?.video_summary?.false_positive_rate ?? null,
      falsePositiveVideos: value?.video_summary?.false_positive_videos ?? null,
      videoCount: value?.video_summary?.video_count ?? null,
      cycleFalsePositiveRate: value?.cycle_summary?.false_positive_rate ?? null,
      falsePositiveCycles: value?.cycle_summary?.false_positive_cycles ?? null,
      cycleCount: value?.cycle_summary?.cycle_count ?? null,
    }))
    .filter((entry) => (entry.falsePositiveVideos ?? 0) > 0 || (entry.falsePositiveCycles ?? 0) > 0)
    .sort((left, right) => {
      const videoDelta = (right.videoFalsePositiveRate ?? -1) - (left.videoFalsePositiveRate ?? -1)
      if (videoDelta !== 0) {
        return videoDelta
      }
      return (right.cycleFalsePositiveRate ?? -1) - (left.cycleFalsePositiveRate ?? -1)
    })
    .slice(0, 5)

  return {
    evaluatedLabels: Object.keys(summary).length,
    topOffenders,
  }
}

function summarizeNegativePushSummary(summary) {
  if (!summary || typeof summary !== 'object') {
    return null
  }

  const topOffenders = Object.entries(summary)
    .map(([label, value]) => ({
      label,
      falsePositiveRate: value?.false_positive_rate ?? null,
      falsePositiveCycles: value?.false_positive_cycles ?? null,
      cycleCount: value?.cycle_count ?? null,
    }))
    .filter((entry) => (entry.falsePositiveCycles ?? 0) > 0)
    .sort((left, right) => (right.falsePositiveRate ?? -1) - (left.falsePositiveRate ?? -1))
    .slice(0, 5)

  return {
    evaluatedLabels: Object.keys(summary).length,
    topOffenders,
  }
}

function summarizeGestureRecommendations(recommendations) {
  if (!recommendations || typeof recommendations !== 'object') {
    return []
  }

  return Object.entries(recommendations)
    .sort(([leftKey], [rightKey]) => leftKey.localeCompare(rightKey))
    .slice(0, 8)
    .map(([key, value]) => ({ key, value }))
}

function summarizeGestureBenchmark() {
  const payload = readJson(path.join(reportsRoot, 'gestures', 'gesture_benchmark.json'))
  if (!payload) {
    return null
  }

  const videoSummary = payload.video_summary ?? {}
  const sequenceSummary = payload.sequence_shadow_summary ?? {}

  return {
    corpus: {
      path: payload.videos_dir ?? null,
      videoCount: videoSummary.video_count ?? null,
      targetVideoAccuracy: payload.target_video_accuracy ?? null,
    },
    accuracy: {
      overallVideoAccuracy: videoSummary.video_accuracy ?? null,
      passesTarget: payload.passes_video_accuracy_target ?? false,
      perGestureVideoAccuracy: videoSummary.per_gesture_video_accuracy ?? {},
    },
    confusions: {
      topPairs: summarizeGestureConfusions(videoSummary.failures ?? []),
    },
    negatives: {
      swipe: summarizeNegativeSwipeSummary(payload.negative_swipe_summary),
      push: summarizeNegativePushSummary(payload.negative_push_summary),
    },
    sequence: {
      videoCount: sequenceSummary.video_count ?? null,
      heuristicAccuracy: sequenceSummary.heuristic_accuracy ?? null,
      heuristicCorrectVideos: sequenceSummary.heuristic_correct_videos ?? null,
      sequenceAccuracy: sequenceSummary.sequence_accuracy ?? null,
      sequenceCorrectVideos: sequenceSummary.sequence_correct_videos ?? null,
      changedPredictions: sequenceSummary.changed_predictions ?? null,
      netCorrectDelta: sequenceSummary.net_correct_delta ?? null,
      promotionReady: sequenceSummary.promotion_ready ?? false,
      passesPromotionGate: payload.passes_sequence_promotion_gate ?? false,
    },
    recommendations: summarizeGestureRecommendations(payload.recommendations),
  }
}

function buildHotspots(backendCc, backendMi, backendHal, eslintSummary) {
  const hotspots = []

  for (const item of backendCc.slice(0, 4)) {
    hotspots.push({
      area: 'backend',
      file: item.file,
      reason: `Cyclomatic complexity ${item.complexity} in ${item.name}`,
    })
  }

  for (const item of backendMi.slice(0, 2)) {
    hotspots.push({
      area: 'backend',
      file: item.file,
      reason: `Maintainability index ${item.mi}`,
    })
  }

  for (const item of backendHal.slice(0, 1)) {
    hotspots.push({
      area: 'backend',
      file: item.file,
      reason: `High Halstead volume ${item.volume}`,
    })
  }

  if (eslintSummary) {
    for (const item of (eslintSummary.topFiles || []).slice(0, 3)) {
      hotspots.push({
        area: 'frontend',
        file: item.file,
        reason: `ESLint findings ${item.errors} errors, ${item.warnings} warnings`,
      })
    }
  }

  const ranked = []
  const seen = new Set()
  for (const hotspot of hotspots) {
    const key = `${hotspot.area}:${hotspot.file}:${hotspot.reason}`
    if (!seen.has(key)) {
      seen.add(key)
      ranked.push(hotspot)
    }
  }

  return ranked.slice(0, 10)
}

function buildNotes(thresholds) {
  const phase2Gates = thresholds?.gates?.phase2
  const gestureNotes = Array.isArray(thresholds?.gestures?.notes) ? thresholds.gestures.notes : []

  if (thresholds?.mode === 'report-only') {
    return [
      'This first slice is report-only. Tool failures and weak metrics are surfaced in the summary but do not enforce merge gates yet.',
      'CBO, LCOM4, DIT, NOC and runtime reliability metrics remain intentionally out of scope for this first implementation slice.',
      ...gestureNotes,
    ]
  }

  const notes = [
    'Phase 2 enables cautious CI gates for required tool steps, backend line coverage, duplication, and zero frontend ESLint errors.',
    'CBO, LCOM4, DIT, NOC and runtime reliability metrics remain intentionally out of scope for this implementation slice.',
  ]

  if (phase2Gates?.notes && Array.isArray(phase2Gates.notes)) {
    notes.push(...phase2Gates.notes)
  }

  notes.push(...gestureNotes)

  return notes
}

function statusSummary(status) {
  return {
    success: status.success,
    steps: status.steps.map((step) => ({
      label: step.label,
      success: step.success,
      exitCode: step.exitCode,
      outputFile: step.outputFile,
    })),
    error: status.error || null,
  }
}

const backendStatus = readStatus('backend')
const frontendStatus = readStatus('frontend')
const duplicationStatus = readStatus('shared')
const gestureStatus = readStatus('gestures')
const thresholds = readJson(thresholdsPath, {})

const backendCc = parseRadonCc()
const backendMi = parseRadonMi()
const backendHal = parseRadonHal()
const backendRaw = parseRadonRaw()
const backendLint = summarizeBackendFlake8()
const backendCcSummary = summarizeBackendCc(backendCc)
const backendMiSummary = summarizeBackendMi(backendMi)
const backendRawSummary = summarizeBackendRawMetrics(backendRaw)
const eslintSummary = summarizeEslint()
const gestureSummary = summarizeGestureBenchmark()

const summary = {
  generatedAt: new Date().toISOString(),
  mode: thresholds.mode || 'report-only',
  combined_status: {
    backend: backendStatus.success ? 'success' : 'warning',
    frontend: frontendStatus.success ? 'success' : 'warning',
    duplication: duplicationStatus.success ? 'success' : 'warning',
    gestures: gestureStatus.success ? 'success' : 'warning',
    overall: [backendStatus, frontendStatus, duplicationStatus, gestureStatus].every((status) => status.success)
      ? 'success'
      : 'warning',
  },
  thresholds,
  backend: {
    status: statusSummary(backendStatus),
    tests: parseJUnitCounts(path.join(reportsRoot, 'backend', 'pytest.junit.xml')),
    coverage: summarizeCoverageJson(path.join(reportsRoot, 'backend', 'coverage.json')),
    lint: {
      success: backendStatus.steps.find((step) => step.label === 'flake8')?.success ?? false,
      findings: backendLint?.findings ?? null,
      filesWithFindings: backendLint?.filesWithFindings ?? null,
      topCodes: backendLint?.topCodes ?? [],
      categoryCounts: backendLint?.categoryCounts ?? {},
      topFiles: backendLint?.topFiles ?? [],
    },
    typecheck: {
      success: backendStatus.steps.find((step) => step.label === 'mypy')?.success ?? false,
    },
    complexity: {
      topFunctions: backendCc.slice(0, 5),
      highRiskEntries: backendCcSummary.highRiskEntries,
      rankDistribution: backendCcSummary.rankDistribution,
      typeDistribution: backendCcSummary.typeDistribution,
      topFilesByComplexity: backendCcSummary.topFiles,
      lowestMaintainability: backendMi.slice(0, 5),
      maintainabilityDistribution: backendMiSummary.rankDistribution,
      maintainabilityBands: backendMiSummary.bands,
      highestHalsteadVolume: backendHal.slice(0, 5),
      largestFiles: backendRawSummary.largestFiles,
      rawSummary: backendRawSummary,
      rawMetrics: backendRaw,
    },
  },
  frontend: {
    status: statusSummary(frontendStatus),
    tests: summarizeVitestResults(),
    coverage: summarizeVitestCoverage(),
    lint: eslintSummary,
    typecheck: {
      success: frontendStatus.steps.find((step) => step.label === 'typecheck')?.success ?? false,
    },
    build: {
      success: frontendStatus.steps.find((step) => step.label === 'build')?.success ?? false,
    },
  },
  duplication: {
    status: statusSummary(duplicationStatus),
    metrics: summarizeDuplication(),
  },
  gestures: {
    status: statusSummary(gestureStatus),
    corpus: gestureSummary?.corpus ?? null,
    accuracy: gestureSummary?.accuracy ?? null,
    confusions: gestureSummary?.confusions ?? { topPairs: [] },
    negatives: gestureSummary?.negatives ?? { swipe: null, push: null },
    sequence: gestureSummary?.sequence ?? null,
    recommendations: gestureSummary?.recommendations ?? [],
  },
  hotspots: buildHotspots(backendCc, backendMi, backendHal, eslintSummary),
  notes: buildNotes(thresholds),
}

writeText(path.join(reportsRoot, 'summary.json'), JSON.stringify(summary, null, 2))

const gestureConfusions = summary.gestures.confusions?.topPairs ?? []
const negativeSwipeOffenders = summary.gestures.negatives?.swipe?.topOffenders ?? []
const negativePushOffenders = summary.gestures.negatives?.push?.topOffenders ?? []

const markdownLines = [
  '# Quality Metrics Summary',
  '',
  `- Generated at: ${summary.generatedAt}`,
  `- Mode: ${summary.mode}`,
  `- Overall status: ${summary.combined_status.overall}`,
  '',
  '## Backend',
  '',
  `- Status: ${summary.combined_status.backend}`,
  `- Tests: ${summary.backend.tests ? `${summary.backend.tests.total} total, ${summary.backend.tests.failed} failed, ${summary.backend.tests.errors} errors, ${summary.backend.tests.skipped} skipped` : 'n/a'}`,
  `- Line coverage: ${summary.backend.coverage?.linesPct ?? 'n/a'}%`,
  `- Branch coverage: ${summary.backend.coverage?.branchesMeasured ? `${summary.backend.coverage?.branchesPct ?? 'n/a'}%` : 'not measured'}`,
  `- Mypy: ${summary.backend.typecheck.success ? 'ok' : 'warning'}`,
  `- Flake8: ${summary.backend.lint.success ? 'ok' : 'warning'}${summary.backend.lint.findings !== null ? ` (${summary.backend.lint.findings} findings)` : ''}`,
  `- High-risk complexity entries (rank C+): ${summary.backend.complexity.highRiskEntries ?? 'n/a'}`,
  '',
  '## Frontend',
  '',
  `- Status: ${summary.combined_status.frontend}`,
  `- Tests: ${summary.frontend.tests ? `${summary.frontend.tests.total} total, ${summary.frontend.tests.failed} failed, ${summary.frontend.tests.skipped} skipped` : 'n/a'}`,
  `- Line coverage: ${summary.frontend.coverage?.linesPct ?? 'n/a'}%`,
  `- Typecheck: ${summary.frontend.typecheck.success ? 'ok' : 'warning'}`,
  `- Build: ${summary.frontend.build.success ? 'ok' : 'warning'}`,
  `- ESLint: ${summary.frontend.lint ? `${summary.frontend.lint.errors} errors, ${summary.frontend.lint.warnings} warnings` : 'n/a'}`,
  '',
  '## Duplication',
  '',
  `- Status: ${summary.combined_status.duplication}`,
  `- Duplication: ${summary.duplication.metrics?.percentage ?? 'n/a'}%`,
  `- Clones: ${summary.duplication.metrics?.clones ?? 'n/a'}`,
  '',
  '## Gestures',
  '',
  `- Status: ${summary.combined_status.gestures}`,
  `- Corpus: ${summary.gestures.corpus ? `${summary.gestures.corpus.path} (${summary.gestures.corpus.videoCount ?? 'n/a'} videos)` : 'n/a'}`,
  `- Video accuracy: ${summary.gestures.accuracy ? `${summary.gestures.accuracy.overallVideoAccuracy ?? 'n/a'} (target ${summary.gestures.corpus?.targetVideoAccuracy ?? 'n/a'}, report-only ${summary.gestures.accuracy.passesTarget ? 'pass' : 'miss'})` : 'n/a'}`,
  `- Top confusion pairs: ${gestureConfusions.length ? gestureConfusions.map((entry) => `${entry.expected} -> ${entry.detected} (${entry.count})`).join('; ') : 'none'}`,
  `- Negative swipe summary: ${negativeSwipeOffenders.length ? negativeSwipeOffenders.map((entry) => `${entry.label}=${entry.videoFalsePositiveRate ?? entry.cycleFalsePositiveRate ?? 'n/a'}`).join('; ') : 'none'}`,
  `- Negative push summary: ${negativePushOffenders.length ? negativePushOffenders.map((entry) => `${entry.label}=${entry.falsePositiveRate ?? 'n/a'}`).join('; ') : 'none'}`,
  `- Sequence shadow: ${summary.gestures.sequence ? `${summary.gestures.sequence.sequenceAccuracy ?? 'n/a'} accuracy, promotion ready ${summary.gestures.sequence.promotionReady ? 'yes' : 'no'}, net delta ${summary.gestures.sequence.netCorrectDelta ?? 'n/a'}` : 'n/a'}`,
  `- Recommendation excerpts: ${summary.gestures.recommendations.length ? summary.gestures.recommendations.map((entry) => `${entry.key}=${entry.value}`).join('; ') : 'none'}`,
  '',
  '## Hotspots',
  '',
]

for (const hotspot of summary.hotspots) {
  markdownLines.push(`- ${hotspot.area}: ${hotspot.file} -> ${hotspot.reason}`)
}

markdownLines.push('', '## Notes', '')
for (const note of summary.notes) {
  markdownLines.push(`- ${note}`)
}

writeText(path.join(reportsRoot, 'summary.md'), markdownLines.join('\n'))