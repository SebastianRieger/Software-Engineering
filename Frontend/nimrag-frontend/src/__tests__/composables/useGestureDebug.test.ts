import { describe, expect, it } from 'vitest'

import { useGestureDebug } from '../../composables/useGestureDebug'
import type { RealtimeEvent } from '../../types/realtime'

const timestamp = '2026-05-30T14:00:00.000Z'

describe('useGestureDebug', () => {
  it('records tracking, gesture, command, action, and frontend dispatch state', () => {
    const debug = useGestureDebug()

    debug.recordRealtimeEvent({
      eventType: 'HandTrackingUpdated',
      payload: {
        hands: [
          {
            hand: 'right',
            landmarks: {
              index_tip: [0.2, 0.3],
              thumb_tip: [0.1, 0.2],
            },
          },
        ],
      },
    })

    debug.recordRealtimeEvent({
      eventType: 'GestureDetected',
      payload: {
        gesture: 'circle',
        timestamp,
        source: 'camera',
        hand: 'right',
        confidence: 0.91,
        tracking_source: 'trajectory',
        tracking_quality: 0.95,
        active_phase: 'committing',
        candidate_scores: { circle: 0.91 },
        reject_reason: null,
        spec_id: 'circle-v1',
        dominant_hand_pose: 'fist',
        primitive_hits: { circular_motion: 0.88 },
      },
    })

    debug.recordRealtimeEvent({
      eventType: 'CommandMatchEvaluated',
      payload: {
        input_source: 'gesture',
        raw_input: 'circle',
        timestamp,
        outcome: 'accepted',
        action: 'toggle_edit_mode',
        reason: null,
        action_args: {},
        metadata: {},
      },
    })

    const actionEvent: RealtimeEvent = {
      eventType: 'UIActionRequested',
      payload: {
        action: 'toggle_edit_mode',
        timestamp,
        input_source: 'gesture',
        raw_input: 'circle',
        action_args: {},
        metadata: {},
      },
    }

    debug.recordRealtimeEvent(actionEvent)
    if (actionEvent.eventType === 'UIActionRequested') {
      debug.recordDispatchResult(actionEvent.payload, true)
    }

    expect(debug.trackingStatus.value).toBe('1 hand(s), 2 points')
    expect(debug.lastGesture.value).toBe('circle')
    expect(debug.lastCommand.value).toBe('toggle_edit_mode')
    expect(debug.lastCommandDetail.value).toBe('accepted')
    expect(debug.lastAction.value).toBe('toggle_edit_mode')
    expect(debug.lastDispatch.value).toBe('handled')
    expect(debug.entries.value.map((entry) => entry.type)).toEqual([
      'frontend',
      'action',
      'command',
      'gesture',
      'tracking',
    ])
  })

  it('records suppressed commands and blocked frontend dispatches as warnings', () => {
    const debug = useGestureDebug()

    debug.recordRealtimeEvent({
      eventType: 'CommandMatchEvaluated',
      payload: {
        input_source: 'gesture',
        raw_input: 'circle',
        timestamp,
        outcome: 'suppressed',
        action: 'toggle_edit_mode',
        reason: 'global_cooldown',
        action_args: {},
        metadata: {},
      },
    })

    debug.recordDispatchResult({
      action: 'resize_expand',
      timestamp,
      input_source: 'gesture',
      raw_input: 'push_click_short',
      action_args: {},
      metadata: {},
    }, false)

    expect(debug.lastCommandDetail.value).toBe('suppressed (global_cooldown)')
    expect(debug.lastDispatch.value).toBe('blocked')
    expect(debug.entries.value[0]?.tone).toBe('warn')
    expect(debug.entries.value[1]?.tone).toBe('warn')
  })
})
