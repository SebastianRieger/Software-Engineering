# API Module Architecture Analysis

## Scope

- Snapshot basis: 5 files and 443 lines in `Backend/src/api`
- Included structure: `__init__.py`, `system_endpoints.py`, `device_endpoints.py` and `data_endpoints.py`
- New calibration surface: lifecycle, analysis and apply or rollback endpoints live alongside the existing config and gesture routes

## Metric View

| Endpoint module | Lines | Status |
| --- | ---: | --- |
| `system_endpoints.py` | 299 | Configuration, gesture runtime, calibration lifecycle and system status |
| `data_endpoints.py` | 67 | Weather plus placeholder calendar and smart-home routes |
| `device_endpoints.py` | 63 | LED, voice control and audio input discovery surface |
| `__init__.py` | 18 | Router aggregation |

## Structure And Logic

The API layer is still intentionally thin. The major change is that `system_endpoints.py` now owns one more real vertical: multimodal input configuration on top of calibration. This file now groups persisted tuning, modality-generic `input-actions`, runtime gesture control and the calibration lifecycle that generates new tuning recommendations.

Hardware discovery also moved from implicit runtime assumptions into explicit API surfaces. Gesture camera enumeration now lives next to the gesture runtime routes, while `device_endpoints.py` exposes audio input discovery alongside voice start, stop and status. This keeps multi-device selection in the same HTTP boundary as the runtime controls the frontend actually invokes.

The calibration API follows the same boundary style as the rest of the module. Request and response validation stays in `schemas`, orchestration stays in `services`, and persistence stays in `repositories`. The HTTP layer only maps domain exceptions to FastAPI responses and triggers the runtime config reload after apply or rollback.

The same boundary principle now also applies to semantic input mappings. The preferred route name is `/api/v1/config/input-actions`, while the legacy `/gesture-actions` alias remains available for compatibility. That keeps the domain wording aligned with the actual code: gestures and voice both consume the same mapping configuration.

## Critical Assessment

- The API remains thin even after adding calibration.
- `system_endpoints.py` is now clearly the largest concentration point in the backend HTTP layer.
- The new calibration routes are coherent with existing config routes because they all manage input behavior, but the file is approaching the threshold where a later split into dedicated config and calibration modules may become worthwhile.
- Conflict handling is now explicit: gesture-config writes are rejected while a gesture-calibration session is active.

## Intended But Missing Elements

- auth and authorization dependencies on sensitive routes
- real calendar and smart-home integrations behind placeholder routes
- optional split of calibration routes out of `system_endpoints.py` if the surface grows further
- active-session discovery or history listing endpoints for richer admin or settings UIs

## Navigation

- Parent: `../backendArch.md`