import { describe, expect, it } from 'vitest'

import {
  classifyMusicalTrainingCaptureError,
  evaluateMusicalTrainingEnvironment,
} from '../utils/musicalTrainingDiagnostics'

describe('evaluateMusicalTrainingEnvironment', () => {
  it('does not report secure-context failure for localhost-only development contexts', () => {
    const result = evaluateMusicalTrainingEnvironment({
      isSecureContext: false,
      hostname: 'localhost',
      topLevel: true,
      hasMediaDevices: true,
      hasGetUserMedia: true,
      hasAudioContext: true,
      permissionState: 'prompt',
      inputDeviceCount: 1,
    })

    expect(result.ready).toBe(true)
    expect(result.diagnostics.some((diagnostic) => diagnostic.code === 'secure_context_missing')).toBe(false)
  })

  it('reports missing secure context for remote hosts', () => {
    const result = evaluateMusicalTrainingEnvironment({
      isSecureContext: false,
      hostname: 'example.test',
      topLevel: true,
      hasMediaDevices: true,
      hasGetUserMedia: true,
      hasAudioContext: true,
      permissionState: 'granted',
      inputDeviceCount: 1,
    })

    expect(result.ready).toBe(false)
    expect(result.diagnostics.some((diagnostic) => diagnostic.code === 'secure_context_missing')).toBe(true)
  })

  it('reports denied permissions and missing input devices as blocking issues', () => {
    const result = evaluateMusicalTrainingEnvironment({
      isSecureContext: true,
      hostname: 'localhost',
      topLevel: true,
      hasMediaDevices: true,
      hasGetUserMedia: true,
      hasAudioContext: true,
      permissionState: 'denied',
      inputDeviceCount: 0,
    })

    expect(result.ready).toBe(false)
    expect(result.diagnostics.map((diagnostic) => diagnostic.code)).toContain('permission_denied')
    expect(result.diagnostics.map((diagnostic) => diagnostic.code)).toContain('no_input_devices')
  })
})

describe('classifyMusicalTrainingCaptureError', () => {
  it('maps NotAllowedError to permission_denied', () => {
    const diagnostic = classifyMusicalTrainingCaptureError(new DOMException('blocked', 'NotAllowedError'))
    expect(diagnostic.code).toBe('permission_denied')
  })

  it('falls back to generic message handling for unknown errors', () => {
    const diagnostic = classifyMusicalTrainingCaptureError(new Error('custom failure'))
    expect(diagnostic.code).toBe('media_devices_unavailable')
    expect(diagnostic.message).toContain('custom failure')
  })
})