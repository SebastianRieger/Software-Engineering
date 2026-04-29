// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CommandSettingsPanel from '../components/manager/CommandSettingsPanel.vue'
import type { CommandProfilesConfig, MusicalAudioConfig, MusicalAudioTrainingArtifact } from '../types/commands'
import type { MusicalAudioStatusResponse } from '../types/hardware'

class FakeAudioContext {
  sampleRate = 48_000

  close() {
    return Promise.resolve()
  }
}

const enumerateDevices = vi.fn(async () => [
  { kind: 'audioinput', deviceId: 'browser-mic-1', label: 'Browser Mic 1' },
  { kind: 'audioinput', deviceId: 'browser-mic-2', label: 'Browser Mic 2' },
])

const queryPermission = vi.fn(async () => ({ state: 'prompt' as const }))

function buildCommandProfiles(): CommandProfilesConfig {
  return {
    active_profile_id: 'default',
    updated_at: null,
    profiles: [
      {
        profile_id: 'default',
        display_name: 'Default Profile',
        description: 'Main test profile',
        updated_at: null,
        input_action_config: {
          mappings: [
            {
              input_source: 'musical_audio',
              raw_input: 'melody.focus_mode',
              action: 'toggle_shop',
              enabled: true,
              metadata: {},
            },
          ],
          global_cooldown_seconds: 0.4,
          repeat_same_action_window_seconds: 0.6,
          source_priorities: {
            gesture: 80,
            voice: 100,
            musical_audio: 90,
            keyboard: 70,
            dev: 100,
          },
          updated_at: null,
        },
        modality_settings: {
          gesture: { enabled: true, active_training_artifact_id: null, metadata: {} },
          voice: { enabled: true, active_training_artifact_id: null, metadata: {} },
          musical_audio: { enabled: true, active_training_artifact_id: 'artifact-a', metadata: {} },
          keyboard: { enabled: true, active_training_artifact_id: null, metadata: {} },
          dev: { enabled: true, active_training_artifact_id: null, metadata: {} },
        },
        device_preferences: {
          gesture_camera_index: 0,
          voice_device_index: 2,
          musical_audio_device_index: 5,
        },
      },
    ],
  }
}

function buildMusicalAudioConfig(): MusicalAudioConfig {
  return {
    enabled: false,
    device_index: 99,
    sample_rate: 16_000,
    block_size: 2048,
    queue_max_chunks: 16,
    silence_threshold: 0.02,
    pitch_confidence_threshold: 0.72,
    command_cooldown_seconds: 0.9,
    min_pattern_notes: 4,
    max_pattern_window_seconds: 5.5,
    active_artifact_id: null,
    updated_at: null,
  }
}

function buildArtifacts(): MusicalAudioTrainingArtifact[] {
  return [
    {
      artifact_id: 'artifact-a',
      profile_id: 'default',
      raw_input: 'melody.focus_mode',
      display_name: 'Focus Mode',
      source_hint: 'whistle',
      notes: [
        { relative_pitch_semitones: 0, relative_time_seconds: 0, duration_seconds: 0.2, confidence: 0.9 },
      ],
      match_threshold: 2.5,
      minimum_confidence: 0.7,
      sample_count: 6,
      enabled: true,
      created_at: null,
      updated_at: null,
      metadata: {},
    },
    {
      artifact_id: 'artifact-b',
      profile_id: 'default',
      raw_input: 'melody.alt_mode',
      display_name: 'Alt Mode',
      source_hint: 'whistle',
      notes: [
        { relative_pitch_semitones: 0, relative_time_seconds: 0, duration_seconds: 0.2, confidence: 0.9 },
        { relative_pitch_semitones: 3, relative_time_seconds: 0.35, duration_seconds: 0.2, confidence: 0.88 },
      ],
      match_threshold: 2.5,
      minimum_confidence: 0.7,
      sample_count: 5,
      enabled: true,
      created_at: null,
      updated_at: null,
      metadata: {},
    },
  ]
}

function buildStatus(): MusicalAudioStatusResponse {
  return {
    message: 'Musical audio status',
    available: true,
    enabled: true,
    running: false,
    status_code: 'ready',
    mode: 'direct-mic',
    provider: 'aubio+dtaidistance',
    active_profile_id: 'default',
    device_index: null,
    device_name: null,
    sample_rate: 16_000,
    block_size: 2048,
    queue_max_chunks: 16,
    active_artifact_id: 'artifact-a',
    artifacts_loaded: 1,
    validated_device_index: 5,
    validated_sample_rate: 48_000,
    last_pitch_hz: null,
    last_match: null,
    last_match_score: null,
    last_event_at: null,
    last_error: null,
    last_error_code: null,
  }
}

function mountPanel() {
  return mount(CommandSettingsPanel, {
    props: {
      commandProfiles: buildCommandProfiles(),
      musicalAudioConfig: buildMusicalAudioConfig(),
      artifacts: buildArtifacts(),
      gestureDevices: [{ index: 0, name: 'Integrated Cam', available: true, backend: 'opencv' }],
      voiceDevices: [
        { index: 2, name: 'Voice Mic', max_input_channels: 1, default_samplerate: 48_000, is_default: false },
      ],
      musicalAudioDevices: [
        { index: 5, name: 'Backend USB Mic', max_input_channels: 1, default_samplerate: 48_000, is_default: true },
      ],
      musicalAudioStatus: buildStatus(),
      loading: false,
      saving: false,
      error: null,
    },
    attachTo: document.body,
  })
}

function findButtonByText(wrapper: ReturnType<typeof mountPanel>, text: string) {
  return wrapper.findAll('button').find((entry) => entry.text().includes(text))
}

function findSelectWithOption(wrapper: ReturnType<typeof mountPanel>, optionValue: string) {
  return wrapper.findAll('select').find((entry) => Array.from((entry.element as HTMLSelectElement).options).some((option) => option.value === optionValue))
}

beforeEach(() => {
  Object.defineProperty(window, 'AudioContext', {
    configurable: true,
    value: FakeAudioContext,
  })
  Object.defineProperty(window, 'isSecureContext', {
    configurable: true,
    value: true,
  })
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getUserMedia: vi.fn(),
      enumerateDevices,
    },
  })
  Object.defineProperty(navigator, 'permissions', {
    configurable: true,
    value: {
      query: queryPermission,
    },
  })
})

afterEach(() => {
  vi.restoreAllMocks()
  enumerateDevices.mockClear()
  queryPermission.mockClear()
  document.body.innerHTML = ''
})

describe('CommandSettingsPanel', () => {
  it('starts the runtime with the device derived from the active profile instead of the config draft', async () => {
    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toContain('Backend USB Mic')
    expect(wrapper.text()).toContain('Quelle: aktives Command-Profil')

    const startButton = findButtonByText(wrapper, 'Runtime starten')
    expect(startButton).toBeDefined()
    await startButton!.trigger('click')

    expect(wrapper.emitted('start-musical-audio')).toEqual([[5]])

    wrapper.unmount()
  })

  it('shows browser-training diagnostics separately from backend runtime information', async () => {
    const wrapper = mountPanel()
    await flushPromises()

    const trainingButton = findButtonByText(wrapper, 'Training')
    expect(trainingButton).toBeDefined()
    await trainingButton!.trigger('click')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Browser-Aufnahmegeraet')
    expect(text).toContain('Backend / sounddevice')
    expect(text).toContain('Web Audio / getUserMedia')
    expect(text).toContain('permission_prompt')
    expect(text).toContain('Der Browser wird beim Start der Aufnahme voraussichtlich nach Mikrofonzugriff fragen.')
    expect(text).not.toContain('secure_context_missing')

    wrapper.unmount()
  })

  it('activates a different artifact through the profile save path', async () => {
    const wrapper = mountPanel()
    await flushPromises()

    const trainingButton = findButtonByText(wrapper, 'Training')
    expect(trainingButton).toBeDefined()
    await trainingButton!.trigger('click')
    await flushPromises()

    const artifactSelect = findSelectWithOption(wrapper, 'artifact-b')
    expect(artifactSelect).toBeDefined()
    await artifactSelect!.setValue('artifact-b')

    const activateButton = findButtonByText(wrapper, 'Als Runtime-Artefakt markieren')
    expect(activateButton).toBeDefined()
    await activateButton!.trigger('click')

    const saveProfileButton = findButtonByText(wrapper, 'Profil speichern')
    expect(saveProfileButton).toBeDefined()
    await saveProfileButton!.trigger('click')

    const emitted = wrapper.emitted('save-command-profiles')
    expect(emitted).toHaveLength(1)

    const savedConfig = emitted?.[0]?.[0] as CommandProfilesConfig
    expect(savedConfig.profiles[0]?.modality_settings.musical_audio.active_training_artifact_id).toBe('artifact-b')
    expect(wrapper.emitted('save-musical-audio-config')).toBeUndefined()

    wrapper.unmount()
  })
})