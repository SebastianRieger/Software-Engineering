# Frontend Src Architecture Analysis

## Scope And Metric Basis

- Snapshot date: 2026-04-28
- Productive frontend files in `Frontend/nimrag-frontend/src`: 24 files and 3493 lines

## Module Metrics

| Scope | Files | Lines | Notes |
| --- | ---: | ---: | --- |
| `components/` | 8 | 2182 | UI, interaction overlay, calibration wizard and orchestration hotspots |
| `services/` | 3 | 261 | REST and websocket clients |
| `types/` | 6 | 324 | Backend contract mirrors including calibration |
| `utils/` | 3 | 648 | Extracted layout, hardware-widget and module-shop helpers |
| `widgets/` | 1 | 62 | Widget registry and defaults |
| `App.vue` and `main.ts` | 2 | 12 | Minimal bootstrap |

## Current Logic Model

The frontend is still organized around one central manager flow, but that flow is now explicitly mode-based. The same application shell can switch between normal gesture-driven UI control and calibration mode without leaving the running app.

The important current layers are:

- orchestration and presentation in `components/manager/*`
- typed backend and realtime access in `services/*`
- manual contract mirrors in `types/*`
- layout and widget helpers in `utils/*`

Calibration did not add a new top-level layer. Instead, it reused those existing ones consistently, which keeps the frontend architecture coherent.

## Critical Assessment

- The frontend has a clearer interactive story than before because calibration is now a real first-class flow.
- The architecture still depends heavily on `ModuleManager.vue` as the central orchestrator.
- The new wizard validates the existing split between components, services, types and utils, but it also increases the pressure for a later shared state layer.
- Automated tests remain the biggest missing frontend quality layer.

## Intended But Missing Elements

- shared frontend state or composables above low-level clients and helpers
- automated tests for manager state, calibration flow and realtime updates
- broader settings or profile-management views if calibration history becomes user-facing

## Navigation

- Parent analysis: `../../../repoArch.md`
- Components module: `components/componentArch.md`
- Services module: `services/serviceArch.md`
- Types module: `types/typeArch.md`
- Utils module: `utils/utilArch.md`