# Backend Src Architecture Analysis

## Scope And Metric Basis

- Snapshot date: 2026-04-14
- Metrics cover productive Python code in `Backend/src` after the API flattening and gesture-service split.
- `Backend/tests` is shown separately because productive code and tests were requested as distinct views.

## Backend Metrics

| Scope | Files | Lines | Notes |
| --- | ---: | ---: | --- |
| `main.py` | 1 | 99 | App bootstrap, lifespan and WebSocket entry point |
| `api/` | 4 | 287 | Flat router package with three domain-grouped endpoint files |
| `core/` | 4 | 189 | Config, DB bootstrap, logging and realtime hub |
| `db/` | 1 | 1 | Placeholder package only |
| `repositories/` | 3 | 339 | Config and weather data access |
| `schemas/` | 7 | 201 | Pydantic request and response contracts |
| `services/` | 7 | 1314 | Business logic center, dominated by the gesture slice |
| Backend tests | 7 | 1336 | Stable backend verification layer |

### Concentration Signals

- `services/` still carries more than half of the backend source volume.
- The gesture slice is no longer a single 903-line file, but it still spans 959 lines across `gestures.py`, `gestures_tracking.py` and `gestures_detection.py`.
- `api/` is now easier to navigate because filesystem version nesting has been removed while the `/api/v1` route prefix remains stable.
- `db/` still exists structurally, but the real database logic remains in `core/database.py`.

## Root Structure Reading

| Element | Current responsibility | Assessment |
| --- | --- | --- |
| `main.py` | Builds the FastAPI app, binds lifecycle and exposes `/ws` | Clean single entry point with sensible lifecycle ownership |
| `api/` | Flat HTTP router package grouped by system, device and data concerns | More discoverable than before, but calendar and smart-home placeholders still inflate perceived domain breadth |
| `core/` | Cross-cutting infrastructure | Useful concentration, though some hardware/provider concerns still want a future adapter boundary |
| `db/` | Reserved package namespace | Still architecturally misleading because it suggests a DB layer that is not actually implemented there |
| `repositories/` | SQLite and external data access | Real repository behavior exists, but only for config and weather |
| `schemas/` | API contracts | Clear and compact, but still incomplete for planned domains |
| `services/` | Application logic and hardware-facing behavior | Valuable layering, now clearer internally, but still uneven in maturity across domains |

## Current Logic Model

The backend is still a modular monolith, now with less internal friction. `main.py` owns startup and shutdown, `api/` groups routes by concern, `services/` orchestrates behavior, `repositories/` handle persistence or provider access, `schemas/` stabilize contracts, and `core/` provides infrastructure. The WebSocket path remains integrated through `core/realtime.py` and the `/ws` endpoint in `main.py`.

The most important improvement is not a new layer, but a clearer one. The API no longer hides its real structure under `api_v1/endpoints`, and the gesture service no longer concentrates tracking, classification and runtime control in one file.

## Missing Intended Elements

- explicit `adapters/` package as described in the target architecture
- production-grade auth and role handling
- real calendar and smart-home implementations behind the placeholder endpoints
- migration strategy and operational health metrics around the SQLite layer
- richer repository coverage once more domains become real

## Critical Assessment

The backend structure is good enough for another project phase and materially better than before, but its growth limits are still visible.

- The API flattening improved maintainability without changing external routes. That is a net simplification with low behavioral risk.
- The gesture refactor removed the worst local monolith, but the gesture domain is still the backend's dominant complexity cluster.
- `db/` remains a structural false friend. New contributors will still expect persistence concerns there, not in `core/database.py`.
- Repository coverage is still narrow. Weather and configuration are real; the rest of the intended integration landscape is still mostly signaled rather than implemented.

## Architecture Diagram

```mermaid
flowchart LR
    Main[main.py\nFastAPI app and lifespan]
    API[api\nflat router package]
    Core[core\nconfig, database, realtime, logging]
    Services[services\napplication logic]
    Repos[repositories\nconfig and weather access]
    Schemas[schemas\nrequest and response models]
    DB[(SQLite via core.database)]
    WS[WebSocket hub]
    PlannedAdapters[Planned adapters package]
    PlannedAuth[Planned auth layer]

    Main --> API
    Main --> Core
    Main --> Services
    API --> Schemas
    API --> Services
    Services --> Repos
    Services --> Core
    Repos --> DB
    Core --> DB
    Core --> WS
    Services --> WS
    Services -. intended extraction .-> PlannedAdapters
    API -. intended protection .-> PlannedAuth
```

## Navigation

- Parent analysis: `../../repoArch.md`
- API module: `api/apiArch.md`
- Core module: `core/coreArch.md`
- DB module: `db/dbArch.md`
- Repository module: `repositories/repoArch.md`
- Schema module: `schemas/schemaArch.md`
- Service module: `services/serviceArch.md`
