# Service Module Architecture Analysis

## Scope

- Snapshot basis: 8 files and 3083 lines in `Backend/src/services`
- Service inventory: gesture runtime, gesture tracking, gesture detection, calibration, led, mqtt, voice and weather

## Metric View

| File | Lines | Reading |
| --- | ---: | --- |
| `calibration.py` | 884 | Session lifecycle, positive-sample analysis, apply, rollback and realtime feedback |
| `gestures.py` | 866 | Gesture runtime facade, gating, semantic action publication and sample forwarding |
| `voice.py` | 482 | Voice service, runtime integration and audio input discovery hotspot |
| `gestures_tracking.py` | 374 | MediaPipe tracking, camera probing, depth-bearing observations and preview extraction |
| `gestures_detection.py` | 263 | Gesture feature extraction, candidate generation and confidence scoring |
| `led.py` | 205 | Hardware-facing service with adapter pattern and state transitions |
| `mqtt.py` | 54 | Early integration scaffold |
| `weather.py` | 27 | Thin facade over repository logic |

## Structure And Logic

The service layer now contains a second real input-behavior vertical next to raw gesture runtime: calibration. `gestures.py` remains the owning runtime for live detection, but it now forwards accepted gesture evidence into `calibration.py` when a gesture-calibration session is active and suppresses normal UI-action publication during that time.

The hardware-facing part of the service layer is also less opaque than before. `gestures_tracking.py` now probes available cameras explicitly and resolves Linux camera names when possible, while `voice.py` enumerates concrete audio input devices from PortAudio. That turns multi-device support from a fixed-index assumption into inspectable runtime state the UI can present.

`calibration.py` is intentionally generic in lifecycle semantics and specific in current analysis strategy. It owns session state, accepted samples, heuristic threshold recommendations, profile persistence triggers and apply or rollback coordination. This keeps the feature inside the normal application boundary instead of drifting into scripts or offline tooling.

## Critical Assessment

- The service layer does real orchestration work and remains the main behavioral center of the backend.
- Input behavior is now split into runtime control and calibration control, which is a substantial maintainability improvement over bolting tuning directly into `gestures.py`.
- The cost is concentration: `gestures.py` and `calibration.py` together now dominate the service layer.
- Voice and MQTT still lag far behind the maturity of the gesture stack.

## Intended But Missing Elements

- real voice calibration built on top of the existing generic calibration lifecycle
- stronger extraction of common measurement or analysis helpers if calibration scope grows
- broader operational telemetry around long-running gesture and calibration sessions
- real MQTT-backed smart-home behavior

## Navigation

- Parent: `../backendArch.md`