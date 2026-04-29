import type { MusicalAudioNoteEvent } from '../types/commands'

export interface MusicalTrainingTake {
  takeId: string
  label: string
  notes: MusicalAudioNoteEvent[]
  durationSeconds: number
  peakLevel: number
  capturedAt: string
}

export interface MusicalTrainingExtractionOptions {
  frameSize?: number
  hopSize?: number
  minAmplitude?: number
  minConfidence?: number
  minNoteDurationSeconds?: number
  maxGapSeconds?: number
  pitchToleranceSemitones?: number
}

interface PitchEstimate {
  hz: number
  confidence: number
  amplitude: number
}

interface AbsoluteNoteEvent {
  pitchMidi: number
  startSeconds: number
  endSeconds: number
  confidence: number
}

function filterTransientOutliers(
  notes: AbsoluteNoteEvent[],
  minNoteDurationSeconds: number,
): AbsoluteNoteEvent[] {
  return notes.filter((note, index, allNotes) => {
    const durationSeconds = note.endSeconds - note.startSeconds
    if (durationSeconds >= minNoteDurationSeconds * 1.5) {
      return true
    }

    const previous = allNotes[index - 1]
    const next = allNotes[index + 1]
    if (!previous || !next) {
      return true
    }

    const previousDistance = Math.abs(note.pitchMidi - previous.pitchMidi)
    const nextDistance = Math.abs(note.pitchMidi - next.pitchMidi)
    return previousDistance <= 5 || nextDistance <= 5
  })
}

function roundTo(value: number, digits: number): number {
  return Number(value.toFixed(digits))
}

function hzToMidi(hz: number): number {
  return 69 + 12 * Math.log2(hz / 440)
}

function totalDuration(notes: MusicalAudioNoteEvent[]): number {
  if (notes.length === 0) {
    return 0
  }

  const lastNote = notes[notes.length - 1]
  return (lastNote?.relative_time_seconds ?? 0) + (lastNote?.duration_seconds ?? 0)
}

export function estimatePitchFromFrame(
  frame: Float32Array,
  sampleRate: number,
  minAmplitude = 0.01,
): PitchEstimate | null {
  const sampleCount = frame.length
  if (sampleCount === 0) {
    return null
  }

  let mean = 0
  let rms = 0
  for (let index = 0; index < sampleCount; index += 1) {
    mean += frame[index] ?? 0
  }
  mean /= sampleCount

  const centered = new Float32Array(sampleCount)
  for (let index = 0; index < sampleCount; index += 1) {
    const value = (frame[index] ?? 0) - mean
    centered[index] = value
    rms += value * value
  }
  rms = Math.sqrt(rms / sampleCount)
  if (rms < minAmplitude) {
    return null
  }

  const minLag = Math.max(8, Math.floor(sampleRate / 1200))
  const maxLag = Math.min(sampleCount - 2, Math.floor(sampleRate / 80))
  const correlations: number[] = []

  let bestLag = -1
  let bestCorrelation = 0

  for (let lag = minLag; lag <= maxLag; lag += 1) {
    let numerator = 0
    let energyA = 0
    let energyB = 0

    for (let index = 0; index < sampleCount - lag; index += 1) {
      const left = centered[index] ?? 0
      const right = centered[index + lag] ?? 0
      numerator += left * right
      energyA += left * left
      energyB += right * right
    }

    if (energyA === 0 || energyB === 0) {
      continue
    }

    const correlation = numerator / Math.sqrt(energyA * energyB)
    correlations[lag] = correlation
    if (correlation > bestCorrelation) {
      bestCorrelation = correlation
      bestLag = lag
    }
  }

  const strongPeakThreshold = Math.max(0.6, bestCorrelation * 0.92)
  for (let lag = minLag + 1; lag < maxLag; lag += 1) {
    const previous = correlations[lag - 1] ?? 0
    const current = correlations[lag] ?? 0
    const next = correlations[lag + 1] ?? 0
    if (current >= strongPeakThreshold && current >= previous && current >= next) {
      bestLag = lag
      bestCorrelation = current
      break
    }
  }

  if (bestLag <= 0 || bestCorrelation < 0.5) {
    return null
  }

  return {
    hz: sampleRate / bestLag,
    confidence: roundTo(bestCorrelation, 3),
    amplitude: roundTo(rms, 4),
  }
}

export function extractNoteEventsFromSamples(
  samples: Float32Array,
  sampleRate: number,
  options: MusicalTrainingExtractionOptions = {},
): MusicalAudioNoteEvent[] {
  const frameSize = options.frameSize ?? 2048
  const hopSize = options.hopSize ?? Math.max(256, Math.floor(frameSize / 4))
  const minAmplitude = options.minAmplitude ?? 0.01
  const minConfidence = options.minConfidence ?? 0.7
  const minNoteDurationSeconds = options.minNoteDurationSeconds ?? 0.08
  const maxGapSeconds = options.maxGapSeconds ?? 0.16
  const pitchToleranceSemitones = options.pitchToleranceSemitones ?? 1.2

  const absoluteNotes: AbsoluteNoteEvent[] = []
  let currentNote: AbsoluteNoteEvent | null = null
  let currentWeight = 0

  const commitCurrentNote = (): void => {
    if (!currentNote) {
      return
    }

    const durationSeconds = currentNote.endSeconds - currentNote.startSeconds
    if (durationSeconds >= minNoteDurationSeconds) {
      absoluteNotes.push({
        ...currentNote,
        confidence: roundTo(currentNote.confidence / Math.max(currentWeight, 1), 3),
      })
    }

    currentNote = null
    currentWeight = 0
  }

  for (let offset = 0; offset + frameSize <= samples.length; offset += hopSize) {
    const frame = samples.slice(offset, offset + frameSize)
    const estimate = estimatePitchFromFrame(frame, sampleRate, minAmplitude)
    const frameStartSeconds = offset / sampleRate
    const frameEndSeconds = (offset + frameSize) / sampleRate

    if (!estimate || estimate.confidence < minConfidence) {
      if (currentNote && frameStartSeconds - currentNote.endSeconds > maxGapSeconds) {
        commitCurrentNote()
      }
      continue
    }

    const midi = hzToMidi(estimate.hz)
    if (!currentNote) {
      currentNote = {
        pitchMidi: midi,
        startSeconds: frameStartSeconds,
        endSeconds: frameEndSeconds,
        confidence: estimate.confidence,
      }
      currentWeight = 1
      continue
    }

    if (Math.abs(midi - currentNote.pitchMidi) <= pitchToleranceSemitones) {
      currentWeight += 1
      currentNote = {
        pitchMidi: ((currentNote.pitchMidi * (currentWeight - 1)) + midi) / currentWeight,
        startSeconds: currentNote.startSeconds,
        endSeconds: frameEndSeconds,
        confidence: currentNote.confidence + estimate.confidence,
      }
      continue
    }

    commitCurrentNote()
    currentNote = {
      pitchMidi: midi,
      startSeconds: frameStartSeconds,
      endSeconds: frameEndSeconds,
      confidence: estimate.confidence,
    }
    currentWeight = 1
  }

  commitCurrentNote()

  const filteredNotes = filterTransientOutliers(absoluteNotes, minNoteDurationSeconds)
  if (filteredNotes.length === 0) {
    return []
  }

  const pitchBaseline = filteredNotes[0]?.pitchMidi ?? 0
  const timeBaseline = filteredNotes[0]?.startSeconds ?? 0

  return filteredNotes.map((note) => ({
    relative_pitch_semitones: roundTo(note.pitchMidi - pitchBaseline, 2),
    relative_time_seconds: roundTo(note.startSeconds - timeBaseline, 2),
    duration_seconds: roundTo(note.endSeconds - note.startSeconds, 2),
    confidence: roundTo(note.confidence, 2),
  }))
}

function noteAtNormalizedPosition(
  notes: MusicalAudioNoteEvent[],
  index: number,
  targetLength: number,
): MusicalAudioNoteEvent {
  const firstNote = notes[0]
  if (!firstNote) {
    return {
      relative_pitch_semitones: 0,
      relative_time_seconds: 0,
      duration_seconds: 0,
      confidence: 0,
    }
  }

  if (notes.length === 1 || targetLength <= 1) {
    return firstNote
  }

  const sourceIndex = Math.round((index / (targetLength - 1)) * (notes.length - 1))
  return notes[Math.max(0, Math.min(notes.length - 1, sourceIndex))] ?? firstNote
}

export function buildTemplateFromAcceptedTakes(takes: MusicalTrainingTake[]): MusicalAudioNoteEvent[] {
  const validTakes = takes.filter((take) => take.notes.length > 0)
  if (validTakes.length === 0) {
    return []
  }

  const averageLength = validTakes.reduce((sum, take) => sum + take.notes.length, 0) / validTakes.length
  const targetLength = Math.max(1, Math.round(averageLength))
  const averageDuration = validTakes.reduce((sum, take) => sum + totalDuration(take.notes), 0) / validTakes.length
  const aggregatedNotes: MusicalAudioNoteEvent[] = []

  for (let index = 0; index < targetLength; index += 1) {
    const bucket = validTakes.map((take) => noteAtNormalizedPosition(take.notes, index, targetLength))
    const averagePitch = bucket.reduce((sum, note) => sum + note.relative_pitch_semitones, 0) / bucket.length
    const averageTime = bucket.reduce((sum, note) => sum + note.relative_time_seconds, 0) / bucket.length
    const averageDurationSeconds = bucket.reduce((sum, note) => sum + (note.duration_seconds ?? 0), 0) / bucket.length
    const averageConfidence = bucket.reduce((sum, note) => sum + (note.confidence ?? 0), 0) / bucket.length

    aggregatedNotes.push({
      relative_pitch_semitones: roundTo(averagePitch, 2),
      relative_time_seconds: roundTo(averageTime, 2),
      duration_seconds: roundTo(averageDurationSeconds, 2),
      confidence: roundTo(averageConfidence, 2),
    })
  }

  const normalized = aggregatedNotes
    .sort((left, right) => left.relative_time_seconds - right.relative_time_seconds)
    .map((note) => ({ ...note }))

  const firstPitch = normalized[0]?.relative_pitch_semitones ?? 0
  const firstTime = normalized[0]?.relative_time_seconds ?? 0
  for (const note of normalized) {
    note.relative_pitch_semitones = roundTo(note.relative_pitch_semitones - firstPitch, 2)
    note.relative_time_seconds = roundTo(note.relative_time_seconds - firstTime, 2)
  }

  if (normalized.length > 1 && averageDuration > 0) {
    const lastTime = normalized[normalized.length - 1]?.relative_time_seconds ?? 0
    const scale = lastTime > 0 ? averageDuration / lastTime : 1
    for (const note of normalized) {
      note.relative_time_seconds = roundTo(note.relative_time_seconds * scale, 2)
    }
  }

  return normalized
}

export function buildContourPolyline(notes: MusicalAudioNoteEvent[], width = 100, height = 32): string {
  if (notes.length === 0) {
    return ''
  }

  const maxTime = Math.max(...notes.map((note) => note.relative_time_seconds + (note.duration_seconds ?? 0)), 0.1)
  const pitches = notes.map((note) => note.relative_pitch_semitones)
  const minPitch = Math.min(...pitches)
  const maxPitch = Math.max(...pitches)
  const pitchSpan = Math.max(1, maxPitch - minPitch)

  return notes
    .map((note) => {
      const x = roundTo((note.relative_time_seconds / maxTime) * width, 2)
      const y = roundTo(height - (((note.relative_pitch_semitones - minPitch) / pitchSpan) * height), 2)
      return `${x},${y}`
    })
    .join(' ')
}