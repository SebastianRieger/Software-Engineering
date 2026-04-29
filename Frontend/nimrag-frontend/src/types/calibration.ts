export type CalibrationModality = 'gesture' | 'voice'
export type CalibrationSessionStatus = 'collecting' | 'analysis_ready' | 'applied' | 'rolled_back' | 'cancelled'

export interface CalibrationModalityDefinition {
  modality: CalibrationModality
  display_name: string
  supported: boolean
}

export interface CalibrationTargetDefinition {
  id: string
  modality: CalibrationModality
  display_name: string
  description: string
  recommended_repetitions_min: number
  recommended_repetitions_max: number
  supported: boolean
}

export interface CalibrationDefinitionsResponse {
  modalities: CalibrationModalityDefinition[]
  targets: CalibrationTargetDefinition[]
}

export interface CalibrationMetricSummary {
  name: string
  min_value: number | null
  max_value: number | null
  mean_value: number | null
  median_value: number | null
  p10_value: number | null
  p90_value: number | null
  sample_count: number
}

export interface CalibrationRecommendation {
  parameter: string
  current_value: number
  recommended_value: number
  min_bound: number | null
  max_bound: number | null
  rationale: string
}

export interface CalibrationTargetProgress {
  target_id: string
  collected_samples: number
  rejected_samples: number
  target_repetitions: number
  completed: boolean
  last_feedback: string | null
  quality_metrics: Record<string, number>
}

export interface CalibrationTargetAnalysis {
  target_id: string
  sample_count: number
  metrics: CalibrationMetricSummary[]
  recommendations: CalibrationRecommendation[]
  artifacts: Record<string, unknown>
  notes: string[]
}

export interface CalibrationAnalysisResult {
  modality: CalibrationModality
  generated_at: string
  targets: CalibrationTargetAnalysis[]
  summary: string | null
}

export interface CalibrationSessionRecord {
  session_id: string
  modality: CalibrationModality
  profile: string
  status: CalibrationSessionStatus
  target_repetitions: number
  selected_targets: string[]
  active_target_id: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
  analysis_ready_at: string | null
  applied_at: string | null
  rolled_back_at: string | null
  cancelled_at: string | null
  progress: CalibrationTargetProgress[]
  analysis: CalibrationAnalysisResult | null
}

export interface CalibrationSessionCreateRequest {
  modality: CalibrationModality
  selected_targets: string[]
  target_repetitions: number
  profile: string
  camera_index?: number
}

export interface CalibrationSessionResponse {
  session: CalibrationSessionRecord
}

export interface CalibrationApplyResponse extends CalibrationSessionResponse {
  applied_profile: {
    modality: CalibrationModality
    profile: string
    source_session_id: string
    saved_at: string
  }
}

export interface CalibrationRollbackResponse extends CalibrationSessionResponse {
  restored_snapshot: {
    modality: CalibrationModality
    profile: string
    source_session_id: string
    captured_at: string
  }
}

export interface CalibrationEventPayload {
  session_id: string
  modality: CalibrationModality
  status: CalibrationSessionStatus | null
  target_id: string | null
  sample_id: string | null
  collected_samples: number | null
  target_repetitions: number | null
  message: string | null
  confidence: number | null
  metadata: Record<string, unknown>
}

export interface CalibrationRealtimeEvent {
  eventType:
    | 'CalibrationSessionStarted'
    | 'CalibrationTargetArmed'
    | 'CalibrationSampleAccepted'
    | 'CalibrationSampleRejected'
    | 'CalibrationTargetCompleted'
    | 'CalibrationAnalysisReady'
    | 'CalibrationProfileApplied'
    | 'CalibrationProfileRolledBack'
  payload: CalibrationEventPayload
}