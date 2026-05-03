# Backend Src Architecture Analysis

## Scope And Metric Basis

- Snapshot date: 2026-04-30
- Productive Python code in `Backend/src` has grown substantially since the previous snapshot; the earlier 30-file / 5244-line figure is no longer current and should be treated as historical context only.
- Backend tests are not part of this file, but the current snapshot is backed by calibration, gesture, config and websocket tests

## Module Metrics

| Scope | Files | Lines | Reading |
| --- | ---: | ---: | --- |
| `main.py` | 1 | ~100 | App bootstrap, lifespan and shared websocket entry point |
| `api/` | 4 | 800+ | Thin HTTP layer for config, runtime, calibration and device control |
| `core/` | 4 | 200+ | Config, DB bootstrap, logging and realtime hub |
| `repositories/` | 3 | 800+ | Config and weather persistence, now including calibration and command-profile storage |
| `schemas/` | 11 | 1200+ | Pydantic contracts for gestures, calibration, interactions, commands, voice and musical audio |
| `services/` | 14 | 7000+ | Gesture runtime, tracking, detection, contracts, offline analysis, calibration, multimodal input orchestration and other domain services |

## Current Logic Model

The backend remains a modular monolith. The major architectural step in this snapshot is that gesture tuning is no longer just static configuration. It is now a runtime capability:

- the gesture subsystem now lives directly under `services/gesture/` instead of a flat compatibility layer.
- `services/gesture/runtime.py` owns live gesture orchestration, while `services/gesture/detection.py`, `services/gesture/tracking.py`, `services/gesture/contracts.py` and `services/gesture/push_runtime.py` carry the extracted gesture-specific logic.
- `services/gesture/offline/` contains the tuner-facing cycle analysis for swipe and push validation runs.
- `services/calibration.py` owns active calibration sessions, accepted sample capture, heuristic analysis, apply, rollback and discard.
- `services/input/orchestrator.py` is now the canonical location of the shared input-to-command path that gestures, voice and musical audio use.
- `repositories/config.py` persists both normal config and calibration artifacts.
- `api/system_endpoints.py` exposes the full calibration lifecycle over HTTP.
- `core/realtime.py` carries calibration feedback over the same websocket channel as the existing interaction events.

This keeps the stack coherent: no parallel storage, no parallel event channel and no one-off offline tuning path.

## Critical Assessment

- The backend structure is materially stronger because calibration was added as a first-class slice rather than a side script.
- The root-module imbalance is not the main problem. The real issue is that `services/` now contains several subsystems in one flat namespace.
- The main hotspot is now shared between gesture runtime, gesture analysis, calibration orchestration and command/input behavior. This is a good sign of product focus, but the flat `services/` layout now hides those boundaries.
- The current best next step is not to create new top-level backend layers, but to continue structuring `services/` internally into gesture and input subpackages while keeping the overall modular-monolith layering intact.
- The modality-generic contracts are a deliberate investment for future voice calibration, but they also introduce some dormant surface area that is not implemented yet.
- Placeholder calendar and smart-home domains remain clearly behind the delivered maturity of the input stack.

## Intended But Missing Elements

- voice calibration implementation on top of the already generic session lifecycle
- further internal splitting of `services/calibration.py` and richer policy extraction inside `services/input/`
- real calendar and smart-home integrations
- stronger migration and retention strategy for long-lived calibration history
- auth, roles and production-grade operational hardening

## Navigation

- Parent analysis: `../../repoArch.md`
- API module: `api/apiArch.md`
- Core module: `core/coreArch.md`
- Repository module: `repositories/repoArch.md`
- Schema module: `schemas/schemaArch.md`
- Service module: `services/serviceArch.md`