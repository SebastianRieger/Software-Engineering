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

The frontend is still organized around one central manager flow, but that flow is now explicitly mode-based and partially extracted into a testable interaction layer. The same application shell can switch between normal multimodal UI control and calibration mode without leaving the running app.

The important current layers are:

- orchestration and presentation in `components/manager/*`
- typed backend and realtime access in `services/*`
- manual contract mirrors in `types/*`
- layout, interaction and widget helpers in `utils/*`

Calibration did not add a new top-level layer. Instead, it reused those existing ones consistently, which keeps the frontend architecture coherent. The same now applies to the command-settings and musical-audio training flow: they extend the existing manager, service, type and util layers instead of introducing a second competing frontend architecture.

## Critical Assessment

- The frontend has a clearer interactive story than before because calibration and command settings are now real first-class flows.
- The architecture still depends heavily on `ModuleManager.vue` as the central orchestrator, but the actual UI-action transitions now live in a pure `interactionReducer` helper instead of being fully embedded in the component.
- The new wizard validates the existing split between components, services, types and utils, but it also increases the pressure for a later shared state layer.
- `CommandSettingsPanel.vue` now concentrates profile editing, device ownership, artifact management and browser-side few-shot training, while `musicalTraining.ts` holds the pure contour extraction and template aggregation logic.
- Automated frontend coverage now includes the interaction reducer and the pure musical-training helpers, but manager integration, websocket flows and the full settings UI still lack broader coverage.

## Intended But Missing Elements

- shared frontend state or composables above low-level clients and helpers
- automated tests for manager state, calibration flow and realtime updates beyond the new reducer slice
- broader settings or profile-management views if calibration history becomes user-facing

## Navigation

- Parent analysis: `../../../repoArch.md`
- Components module: `components/componentArch.md`
- Services module: `services/serviceArch.md`
- Types module: `types/typeArch.md`
- Utils module: `utils/utilArch.md`