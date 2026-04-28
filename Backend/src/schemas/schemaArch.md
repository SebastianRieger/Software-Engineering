# Schema Module Architecture Analysis

## Scope

- Snapshot basis: 8 files and 382 lines in `Backend/src/schemas`
- Domain schema files: configuration, gestures, interactions, led, system, voice and weather

## Metric View

| File | Lines | Responsibility |
| --- | ---: | --- |
| `gestures.py` | 93 | Gesture events, status, config and related payload shapes |
| `configuration.py` | 79 | Placement-based layout and system configuration contracts |
| `interactions.py` | 64 | Semantic input-action mapping and `UIActionRequested` payloads |
| `voice.py` | 64 | Voice status and control contracts |
| `weather.py` | 49 | Weather response contracts |
| `led.py` | 23 | LED state and control contracts |
| `system.py` | 9 | Backend metadata contracts |
| `system.py` | 9 | Backend system metadata contracts |

## Structure And Logic

The schema module is compact and effective. It gives the API layer stable request and response models without leaking service implementation details. It also shows which domains are already materially supported by the backend: gestures, configuration, interactions, weather, LED, voice and system metadata.

The most important change is the new distinction between raw and semantic input contracts. `gestures.py` models detection and tuning, `configuration.py` models placement-based widget persistence, and `interactions.py` models modality-neutral UI actions plus configurable mappings from gestures to those actions. Because the schema layer is still compact, it also exposes the gaps very clearly. There are no calendar or smart-home schemas of substance yet, and there is no shared contract generation path to the TypeScript frontend.

## Critical Assessment

- The schema layer is clean and proportionate to the current backend size.
- Gesture and interaction schemas are already richer than several other domains, which matches the high complexity in the gesture service.
- The module currently relies on disciplined manual synchronization with frontend TypeScript types. That is acceptable now but increases contract drift risk later.
- There is no stronger versioning story for contracts beyond the configured `/api/v1` route prefix and disciplined schema evolution.

## Intended But Missing Elements

- calendar and smart-home contracts once those verticals are real
- a clearer strategy for shared backend and frontend contract evolution
- possible common envelope patterns if the API surface grows more varied

## Diagram

```mermaid
flowchart LR
    API[api endpoints]
    Schemas[schemas module]
    Services[services]
    FrontendTypes[Frontend TypeScript mirrors]
    UIActions[Semantic UIAction contracts]
    PlannedDomains[Planned calendar and smart-home contracts]

    API --> Schemas
    Services --> Schemas
    Schemas --> UIActions
    Schemas -. mirrored manually .-> FrontendTypes
    Schemas -. intended domain growth .-> PlannedDomains
```

## Navigation

- Parent: `../backendArch.md`
