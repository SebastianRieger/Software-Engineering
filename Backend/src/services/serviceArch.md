# Service Module Architecture Analysis

## Scope

- Snapshot basis: 7 files and 2017 lines in `Backend/src/services`
- Service inventory: gesture facade plus tracking and detection helpers, led, mqtt, voice and weather

## Metric View

| File | Lines | Reading |
| --- | ---: | --- |
| `gestures.py` | 685 | Gesture runtime facade, lifecycle, semantic action publication and realtime orchestration |
| `voice.py` | 449 | Voice service and runtime integration hotspot |
| `gestures_tracking.py` | 335 | MediaPipe tracking, depth-bearing observations and preview extraction |
| `gestures_detection.py` | 262 | Gesture feature extraction, candidate generation and confidence scoring |
| `led.py` | 205 | Hardware-facing service with adapter pattern and state transitions |
| `mqtt.py` | 54 | Early integration scaffold |
| `weather.py` | 27 | Thin facade over repository logic |

## Structure And Logic

The service layer is where the backend becomes an application instead of a collection of endpoints. `WeatherService` stays intentionally thin and delegates almost everything to `WeatherRepository`. `LEDService` manages state, adapter application and event publication. The gesture domain now has three explicit responsibilities: runtime orchestration in `gestures.py`, hand tracking and MediaPipe interaction in `gestures_tracking.py`, and normalized detection logic in `gestures_detection.py`. `voice.py` and `mqtt.py` still reserve the intended architecture boundary for later integrations.

Within that gesture slice, the runtime service now does more than publish raw recognition. It also loads configurable gesture-to-action mappings, derives semantic `UIActionRequested` events and maintains the state needed for push-click timing, focus-style navigation gestures and two-hand zoom. This remains the strongest architectural layer and also the layer with the clearest imbalance, just in a more understandable shape than before.

## Critical Assessment

- The service layer does real work and is not just an anemic wrapper around repositories.
- The gesture slice is still dominant, but it is no longer a single opaque hotspot. That is a meaningful maintainability improvement.
- `gestures.py` is again the primary hotspot because semantic action mapping, cooldown and mode-sensitive runtime control were intentionally centralized there.
- `weather.py` remains intentionally thin, which is fine today and keeps weather logic close to the repository boundary.
- `voice.py` and `mqtt.py` still communicate target intent more than delivered integration depth.
- There is still no dedicated `adapters/` package even though LED and gestures already behave as if such a boundary conceptually exists.

## Intended But Missing Elements

- mature voice integration instead of status-shell behavior
- real MQTT-backed smart-home behavior
- explicit extraction of adapter-facing concerns from service modules
- broader operational telemetry and health reporting around long-running gesture and hardware services

## Diagram

```mermaid
flowchart LR
    API[api endpoints]
    WeatherService[WeatherService]
    LedService[LEDService]
    GestureFacade[gestures.py]
    GestureTracking[gestures_tracking.py]
    GestureDetection[gestures_detection.py]
    UIActions[UIAction mapping and publication]
    VoiceService[VoiceService]
    MqttService[MqttService]
    Repositories[repositories]
    Core[core config and realtime]
    Hardware[Hardware adapters and devices]
    PlannedAdapters[Planned adapters package]

    API --> WeatherService
    API --> LedService
    API --> GestureFacade
    API --> VoiceService
    API --> MqttService
    GestureFacade --> GestureTracking
    GestureFacade --> GestureDetection
    GestureFacade --> UIActions
    WeatherService --> Repositories
    LedService --> Core
    GestureFacade --> Core
    UIActions --> Core
    VoiceService --> Core
    MqttService --> Core
    LedService --> Hardware
    GestureTracking --> Hardware
    VoiceService -. intended integration .-> Hardware
    MqttService -. intended integration .-> Hardware
    LedService -. intended extraction .-> PlannedAdapters
    GestureFacade -. intended extraction .-> PlannedAdapters
```

## Navigation

- Parent: `../backendArch.md`
