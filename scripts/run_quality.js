const fs = require('node:fs')
const path = require('node:path')
const { spawnSync } = require('node:child_process')

const repoRoot = path.resolve(__dirname, '..')
const frontendRoot = path.join(repoRoot, 'Frontend', 'nimrag-frontend')
const reportsRoot = path.join(repoRoot, 'reports', 'quality')
const mode = process.argv[2]

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true })
}

function resetDir(dirPath) {
  fs.rmSync(dirPath, { recursive: true, force: true })
  ensureDir(dirPath)
}

function writeFile(filePath, content) {
  ensureDir(path.dirname(filePath))
  fs.writeFileSync(filePath, content, 'utf8')
}

function writeJson(filePath, payload) {
  writeFile(filePath, `${JSON.stringify(payload, null, 2)}\n`)
}

function relativePath(filePath) {
  return path.relative(repoRoot, filePath).split(path.sep).join('/')
}

function commandToString(command, args) {
  return [command, ...args].join(' ')
}

function resolvePython() {
  const candidates = [
    path.join(repoRoot, 'Backend', 'venv_py312', 'bin', 'python'),
    path.join(repoRoot, 'Backend', 'venv_py312', 'Scripts', 'python.exe'),
    path.join(repoRoot, 'Backend', '.venv', 'bin', 'python'),
    path.join(repoRoot, 'Backend', '.venv', 'Scripts', 'python.exe'),
    'python3',
    'python',
  ]

  for (const candidate of candidates) {
    const probe = spawnSync(candidate, ['--version'], {
      cwd: repoRoot,
      encoding: 'utf8',
      shell: false,
    })
    if (!probe.error && probe.status === 0) {
      return candidate
    }
  }

  return null
}

function runCommand({ label, command, args, cwd = repoRoot, outputFile }) {
  const startedAt = Date.now()
  const result = spawnSync(command, args, {
    cwd,
    env: { ...process.env, FORCE_COLOR: '0' },
    encoding: 'utf8',
    shell: false,
  })
  const finishedAt = Date.now()
  const combinedOutput = [result.stdout || '', result.stderr || '']
    .filter(Boolean)
    .join(result.stdout && result.stderr ? '\n' : '')

  if (outputFile) {
    writeFile(outputFile, combinedOutput)
  }

  return {
    label,
    command: commandToString(command, args),
    cwd: relativePath(cwd),
    success: !result.error && result.status === 0,
    exitCode: result.error ? 1 : (result.status ?? 1),
    durationMs: finishedAt - startedAt,
    outputFile: outputFile ? relativePath(outputFile) : null,
    error: result.error ? result.error.message : null,
  }
}

function runBackendQuality() {
  const sectionDir = path.join(reportsRoot, 'backend')
  resetDir(sectionDir)

  const python = resolvePython()
  if (!python) {
    writeJson(path.join(sectionDir, 'status.json'), {
      mode: 'backend',
      success: false,
      steps: [],
      error: 'No Python interpreter could be resolved for backend quality checks.',
    })
    return
  }

  const steps = [
    runCommand({
      label: 'pytest',
      command: python,
      args: [
        '-m',
        'pytest',
        'Backend/tests',
        '--cov=Backend/src',
        '--cov-report=xml:reports/quality/backend/coverage.xml',
        '--cov-report=json:reports/quality/backend/coverage.json',
        '--cov-report=term-missing:skip-covered',
        '--junitxml=reports/quality/backend/pytest.junit.xml',
      ],
      outputFile: path.join(sectionDir, 'pytest.txt'),
    }),
    runCommand({
      label: 'mypy',
      command: python,
      args: ['-m', 'mypy', 'Backend/src'],
      outputFile: path.join(sectionDir, 'mypy.txt'),
    }),
    runCommand({
      label: 'flake8',
      command: python,
      args: [
        '-m',
        'flake8',
        'Backend/src',
        'Backend/tests',
        '--statistics',
        '--count',
        '--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s',
      ],
      outputFile: path.join(sectionDir, 'flake8.txt'),
    }),
    runCommand({
      label: 'radon-cc',
      command: python,
      args: ['-m', 'radon', 'cc', 'Backend/src', '-j'],
      outputFile: path.join(sectionDir, 'radon-cc.json'),
    }),
    runCommand({
      label: 'radon-mi',
      command: python,
      args: ['-m', 'radon', 'mi', 'Backend/src', '-j'],
      outputFile: path.join(sectionDir, 'radon-mi.json'),
    }),
    runCommand({
      label: 'radon-hal',
      command: python,
      args: ['-m', 'radon', 'hal', 'Backend/src', '-j'],
      outputFile: path.join(sectionDir, 'radon-hal.json'),
    }),
    runCommand({
      label: 'radon-raw',
      command: python,
      args: ['-m', 'radon', 'raw', 'Backend/src', '-j'],
      outputFile: path.join(sectionDir, 'radon-raw.json'),
    }),
  ]

  writeJson(path.join(sectionDir, 'status.json'), {
    mode: 'backend',
    success: steps.every((step) => step.success),
    steps,
  })
}

function runFrontendQuality() {
  const sectionDir = path.join(reportsRoot, 'frontend')
  resetDir(sectionDir)

  const steps = [
    runCommand({
      label: 'vitest',
      command: 'npm',
      args: [
        'exec',
        '--',
        'vitest',
        'run',
        '--config',
        'vitest.config.ts',
        '--coverage',
        '--reporter=json',
        '--outputFile',
        '../../reports/quality/frontend/vitest.json',
      ],
      cwd: frontendRoot,
      outputFile: path.join(sectionDir, 'vitest.txt'),
    }),
    runCommand({
      label: 'typecheck',
      command: 'npm',
      args: ['run', 'typecheck'],
      cwd: frontendRoot,
      outputFile: path.join(sectionDir, 'typecheck.txt'),
    }),
    runCommand({
      label: 'build',
      command: 'npm',
      args: ['run', 'build:bundle'],
      cwd: frontendRoot,
      outputFile: path.join(sectionDir, 'build.txt'),
    }),
    runCommand({
      label: 'eslint',
      command: 'npm',
      args: [
        'exec',
        '--',
        'eslint',
        'src',
        '--ext',
        '.ts,.vue',
        '-f',
        'json',
        '-o',
        '../../reports/quality/frontend/eslint.json',
      ],
      cwd: frontendRoot,
      outputFile: path.join(sectionDir, 'eslint.txt'),
    }),
  ]

  writeJson(path.join(sectionDir, 'status.json'), {
    mode: 'frontend',
    success: steps.every((step) => step.success),
    steps,
  })
}

function runDuplicationQuality() {
  const sectionDir = path.join(reportsRoot, 'shared')
  resetDir(sectionDir)

  const step = runCommand({
    label: 'jscpd',
    command: 'npm',
    args: [
      'exec',
      '--',
      'jscpd',
      'Backend/src',
      'Frontend/nimrag-frontend/src',
      '--reporters',
      'json,console',
      '--output',
      'reports/quality/shared/jscpd',
      '--pattern',
      '**/*.{py,ts,vue}',
      '--ignore',
      '**/__pycache__/**,**/tests/**,**/dist/**,**/coverage/**,**/graphify-out/**,**/node_modules/**,**/venv_py312/**,**/.venv/**,**/docs/archive/**',
      '--gitignore',
    ],
    outputFile: path.join(sectionDir, 'jscpd.txt'),
  })

  writeJson(path.join(sectionDir, 'status.json'), {
    mode: 'duplication',
    success: step.success,
    steps: [step],
  })
}

function runGestureQuality() {
  const sectionDir = path.join(reportsRoot, 'gestures')
  resetDir(sectionDir)

  const python = resolvePython()
  if (!python) {
    writeJson(path.join(sectionDir, 'status.json'), {
      mode: 'gesture',
      success: false,
      steps: [],
      error: 'No Python interpreter could be resolved for gesture quality checks.',
    })
    return
  }

  const step = runCommand({
    label: 'gesture-benchmark',
    command: python,
    args: [
      path.join('Backend', 'scripts', 'gesture_benchmark.py'),
      '--videos-dir',
      'pics',
      '--output',
      path.join('reports', 'quality', 'gestures', 'gesture_benchmark.json'),
    ],
    outputFile: path.join(sectionDir, 'gesture_benchmark.txt'),
  })

  writeJson(path.join(sectionDir, 'status.json'), {
    mode: 'gesture',
    success: step.success,
    steps: [step],
  })
}

ensureDir(reportsRoot)

switch (mode) {
  case 'backend':
    runBackendQuality()
    break
  case 'frontend':
    runFrontendQuality()
    break
  case 'duplication':
    runDuplicationQuality()
    break
  case 'gesture':
    runGestureQuality()
    break
  default:
    console.error(`Unsupported quality mode: ${mode || '<missing>'}`)
    process.exitCode = 1
}