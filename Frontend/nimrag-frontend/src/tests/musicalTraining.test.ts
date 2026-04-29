import { describe, expect, it } from 'vitest'

import {
  buildContourPolyline,
  buildTemplateFromAcceptedTakes,
  estimatePitchFromFrame,
  extractNoteEventsFromSamples,
  type MusicalTrainingTake,
} from '../utils/musicalTraining'

function buildSineWave(frequency: number, durationSeconds: number, sampleRate = 16_000): Float32Array {
  const sampleCount = Math.floor(durationSeconds * sampleRate)
  const samples = new Float32Array(sampleCount)

  for (let index = 0; index < sampleCount; index += 1) {
    samples[index] = Math.sin((2 * Math.PI * frequency * index) / sampleRate) * 0.75
  }

  return samples
}

function concatSamples(...chunks: Float32Array[]): Float32Array {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const merged = new Float32Array(totalLength)
  let offset = 0

  for (const chunk of chunks) {
    merged.set(chunk, offset)
    offset += chunk.length
  }

  return merged
}

describe('musicalTraining helpers', () => {
  it('estimates the pitch of a simple sine wave', () => {
    const pitch = estimatePitchFromFrame(buildSineWave(440, 0.2), 16_000)

    expect(pitch).not.toBeNull()
    expect(pitch?.hz ?? 0).toBeGreaterThan(430)
    expect(pitch?.hz ?? 0).toBeLessThan(450)
    expect(pitch?.confidence ?? 0).toBeGreaterThan(0.9)
  })

  it('extracts a note contour from monophonic samples', () => {
    const samples = concatSamples(
      buildSineWave(440, 0.28),
      buildSineWave(554.37, 0.28),
      buildSineWave(659.25, 0.28),
    )

    const notes = extractNoteEventsFromSamples(samples, 16_000, {
      frameSize: 1024,
      hopSize: 256,
      minConfidence: 0.75,
      minNoteDurationSeconds: 0.06,
    })

    expect(notes.length).toBeGreaterThanOrEqual(3)
    expect(notes[0]?.relative_pitch_semitones).toBeCloseTo(0, 0)
    expect(notes[1]?.relative_pitch_semitones ?? 0).toBeGreaterThan(2)
    expect(notes[2]?.relative_pitch_semitones ?? 0).toBeGreaterThan(6)
  })

  it('builds an averaged template from accepted takes', () => {
    const takes: MusicalTrainingTake[] = [
      {
        takeId: 'a',
        label: 'Take A',
        durationSeconds: 1.0,
        peakLevel: 0.7,
        capturedAt: '2026-04-29T10:00:00Z',
        notes: [
          { relative_pitch_semitones: 0, relative_time_seconds: 0, duration_seconds: 0.2, confidence: 0.9 },
          { relative_pitch_semitones: 3, relative_time_seconds: 0.3, duration_seconds: 0.2, confidence: 0.9 },
          { relative_pitch_semitones: 7, relative_time_seconds: 0.7, duration_seconds: 0.2, confidence: 0.9 },
        ],
      },
      {
        takeId: 'b',
        label: 'Take B',
        durationSeconds: 1.05,
        peakLevel: 0.68,
        capturedAt: '2026-04-29T10:01:00Z',
        notes: [
          { relative_pitch_semitones: 0, relative_time_seconds: 0, duration_seconds: 0.21, confidence: 0.88 },
          { relative_pitch_semitones: 2.5, relative_time_seconds: 0.34, duration_seconds: 0.19, confidence: 0.87 },
          { relative_pitch_semitones: 6.5, relative_time_seconds: 0.73, duration_seconds: 0.18, confidence: 0.91 },
        ],
      },
    ]

    const template = buildTemplateFromAcceptedTakes(takes)

    expect(template).toHaveLength(3)
    expect(template[0]?.relative_pitch_semitones).toBeCloseTo(0, 2)
    expect(template[1]?.relative_pitch_semitones ?? 0).toBeGreaterThan(2)
    expect(template[2]?.relative_pitch_semitones ?? 0).toBeGreaterThan(6)
  })

  it('creates a preview polyline for contour rendering', () => {
    const polyline = buildContourPolyline([
      { relative_pitch_semitones: 0, relative_time_seconds: 0, duration_seconds: 0.2, confidence: 0.9 },
      { relative_pitch_semitones: 4, relative_time_seconds: 0.4, duration_seconds: 0.2, confidence: 0.9 },
      { relative_pitch_semitones: 2, relative_time_seconds: 0.8, duration_seconds: 0.2, confidence: 0.9 },
    ])

    expect(polyline).toContain('0,')
    expect(polyline.split(' ')).toHaveLength(3)
  })
})