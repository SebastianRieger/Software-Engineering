export type MusicalTrainingPermissionState = PermissionState | 'unsupported' | null

export type MusicalTrainingDiagnosticCode =
  | 'secure_context_missing'
  | 'embedded_context_restricted'
  | 'media_devices_unavailable'
  | 'audio_context_unavailable'
  | 'permission_denied'
  | 'permission_prompt'
  | 'no_input_devices'
  | 'ready'

export interface MusicalTrainingDiagnostic {
  code: MusicalTrainingDiagnosticCode
  severity: 'info' | 'warning' | 'error'
  message: string
}

export interface MusicalTrainingBrowserEnvironment {
  isSecureContext: boolean
  hostname: string
  topLevel: boolean
  hasMediaDevices: boolean
  hasGetUserMedia: boolean
  hasAudioContext: boolean
  permissionState: MusicalTrainingPermissionState
  inputDeviceCount: number | null
}

export interface MusicalTrainingPreflightResult {
  ready: boolean
  diagnostics: MusicalTrainingDiagnostic[]
}

function isLocalHostname(hostname: string): boolean {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]'
}

export function evaluateMusicalTrainingEnvironment(
  environment: MusicalTrainingBrowserEnvironment,
): MusicalTrainingPreflightResult {
  const diagnostics: MusicalTrainingDiagnostic[] = []

  if (!environment.hasMediaDevices || !environment.hasGetUserMedia) {
    diagnostics.push({
      code: 'media_devices_unavailable',
      severity: 'error',
      message: 'MediaDevices oder getUserMedia stehen in diesem Browserkontext nicht zur Verfuegung.',
    })
  }

  if (!environment.hasAudioContext) {
    diagnostics.push({
      code: 'audio_context_unavailable',
      severity: 'error',
      message: 'Web Audio ist in diesem Browserkontext nicht verfuegbar.',
    })
  }

  if (!environment.isSecureContext && !isLocalHostname(environment.hostname)) {
    diagnostics.push({
      code: 'secure_context_missing',
      severity: 'error',
      message: 'Mikrofonaufnahme benoetigt ausserhalb von localhost einen sicheren Kontext (HTTPS).',
    })
  }

  if (!environment.topLevel) {
    diagnostics.push({
      code: 'embedded_context_restricted',
      severity: 'warning',
      message: 'Die Seite laeuft nicht im fokussierten Top-Level-Kontext. Manche Browser blockieren dann Mikrofon-Prompts.',
    })
  }

  if (environment.permissionState === 'denied') {
    diagnostics.push({
      code: 'permission_denied',
      severity: 'error',
      message: 'Der Browser blockiert aktuell den Mikrofonzugriff.',
    })
  }

  if (environment.permissionState === 'prompt') {
    diagnostics.push({
      code: 'permission_prompt',
      severity: 'info',
      message: 'Der Browser wird beim Start der Aufnahme voraussichtlich nach Mikrofonzugriff fragen.',
    })
  }

  if (environment.inputDeviceCount === 0) {
    diagnostics.push({
      code: 'no_input_devices',
      severity: 'error',
      message: 'Es wurden keine Browser-Audioeingabegeraete erkannt.',
    })
  }

  if (diagnostics.length === 0) {
    diagnostics.push({
      code: 'ready',
      severity: 'info',
      message: 'Browser-Training ist bereit. Runtime- und Browser-Geraet sind bewusst getrennt.',
    })
  }

  return {
    ready: diagnostics.every((diagnostic) => diagnostic.severity !== 'error'),
    diagnostics,
  }
}

export function classifyMusicalTrainingCaptureError(error: unknown): MusicalTrainingDiagnostic {
  if (error instanceof DOMException) {
    if (error.name === 'NotAllowedError' || error.name === 'SecurityError') {
      return {
        code: 'permission_denied',
        severity: 'error',
        message: 'Der Browser hat den Mikrofonzugriff verweigert oder einen Security-Block ausgelost.',
      }
    }

    if (error.name === 'NotFoundError') {
      return {
        code: 'no_input_devices',
        severity: 'error',
        message: 'Das gewaehlte Browser-Aufnahmegeraet ist nicht verfuegbar.',
      }
    }

    if (error.name === 'NotReadableError') {
      return {
        code: 'embedded_context_restricted',
        severity: 'error',
        message: 'Das Mikrofon konnte nicht geoeffnet werden. Geraet belegt, Browser-Block oder OS-Sperre sind moeglich.',
      }
    }
  }

  return {
    code: 'media_devices_unavailable',
    severity: 'error',
    message: error instanceof Error
      ? error.message
      : 'Mikrofonaufnahme konnte in diesem Browserkontext nicht gestartet werden.',
  }
}