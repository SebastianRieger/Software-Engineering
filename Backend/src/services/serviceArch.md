# Service Module Architecture Analysis

## Scope

- Snapshot basis: the service layer has outgrown the earlier 8-file snapshot and now contains multiple internal subsystems.
- Service inventory now includes gesture runtime, gesture tracking, gesture detection, gesture contracts, push runtime, offline gesture cycle analysis, calibration, multimodal input orchestration, voice, musical audio, led, mqtt and weather.

## Metric View

| File | Lines | Reading |
| --- | ---: | --- |
| `calibration.py` | 800+ | Session lifecycle, positive-sample analysis, apply, rollback and realtime feedback |
| `gesture/runtime.py` | 1200+ | Live gesture orchestrator, semantic event publication and calibration-sample capture |
| `gesture/tracking.py` | 1100+ | MediaPipe tracking, camera probing, hand observations, pose features and preview extraction |
| `gesture/detection.py` | 900+ | Gesture feature extraction, primitive scoring, specs and runtime analysis |
| `gesture/contracts.py` | 300+ | Canonical gesture execution contracts for tuning and user-facing documentation |
| `gesture/push_runtime.py` | 250+ | Push click state machine separate from general runtime arbitration |
| `gesture/offline/push_cycle_analysis.py` | 250+ | Offline push cycle segmentation and profiling for tuner and benchmarking |
| `gesture/offline/swipe_cycle_analysis.py` | 500+ | Offline swipe cycle segmentation and profiling for tuner and benchmarking |
| `interactions.py` | 170+ | Compatibility wrapper for the shared input orchestrator |
| `voice.py` | 450+ | Voice service, runtime integration, normalized voice raw inputs and audio input discovery hotspot |
| `musical_audio.py` | 800+ | Musical-audio runtime, artifact management and semantic raw-input publication |
| `led.py` | 150+ | Hardware-facing service with adapter pattern and state transitions |
| `mqtt.py` | 50+ | Early integration scaffold |
| `weather.py` | 20+ | Thin facade over repository logic |

## Structure And Logic

The service layer now contains more than one real subsystem. The most important are the gesture subsystem, the calibration subsystem and the shared input-orchestration path for gestures, voice and musical audio.

The current migration direction is to keep the backend root layers stable and structure the service layer internally:

- `services/gesture/` is now the canonical home for gesture runtime, detection, tracking, contracts, push-specific runtime logic and offline analysis.
- `services/input/` is the target home for multimodal raw-input to UI-action orchestration.
- `interactions.py` still acts as a compatibility facade, but the gesture compatibility wrappers have been removed.

The gesture runtime therefore no longer needs to be read as a single file story. `services/gesture/runtime.py` orchestrates the live loop, while `services/gesture/contracts.py`, `services/gesture/detection.py`, `services/gesture/tracking.py` and `services/gesture/push_runtime.py` carry the gesture-specific behavior behind that facade.

The hardware-facing part of the service layer is also less opaque than before. `services/gesture/tracking.py` now probes available cameras explicitly and resolves Linux camera names when possible, while `voice.py` enumerates concrete audio input devices from PortAudio. That turns multi-device support from a fixed-index assumption into inspectable runtime state the UI can present.

`voice.py` now also participates in the same semantic input path as gestures. Recognized transcripts are matched against configured commands, normalized to stable `voice.*` raw inputs and then handed to `services/input/orchestrator.py`, which can publish both `RawInputDetected` and `UIActionRequested` events.

`calibration.py` is intentionally generic in lifecycle semantics and specific in current analysis strategy. It owns session state, accepted samples, heuristic threshold recommendations, profile persistence triggers and apply or rollback coordination. This keeps the feature inside the normal application boundary instead of drifting into scripts or offline tooling.

The offline cycle-analysis modules deserve separate mention: `services/gesture/offline/push_cycle_analysis.py` and `services/gesture/offline/swipe_cycle_analysis.py` are not live runtime services in the same sense as `services/gesture/runtime.py` or `voice.py`. They serve tuner, benchmark and validation workflows and now sit with the rest of the gesture subsystem instead of the flat top-level `services/` namespace.

## Critical Assessment

- The service layer does real orchestration work and remains the main behavioral center of the backend.
- Input behavior is now split into runtime control, command orchestration and calibration control, which is a substantial maintainability improvement over bolting tuning directly into one file.
- The cost is concentration: gesture runtime, tracking, detection and calibration still dominate the service layer and need better internal package boundaries.
- The right answer is not a new root-level backend architecture, but a more explicit internal structure inside `services/`.
- Voice is structurally much closer to the gesture stack than before because both now share the same semantic action path, but calibration and richer arbitration policies are still missing.

## Intended But Missing Elements

- real voice calibration built on top of the existing generic calibration lifecycle
- richer multimodal arbitration and policy handling inside the shared input orchestrator
- continued internal cleanup of calibration and input policy now that gesture logic has already been moved into `services/gesture/`
- stronger extraction of common measurement or analysis helpers if calibration scope grows
- broader operational telemetry around long-running gesture and calibration sessions
- real MQTT-backed smart-home behavior

## Navigation

- Parent: `../backendArch.md`