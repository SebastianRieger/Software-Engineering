# Backend Src Architecture Analysis

## Scope And Metric Basis

- Snapshot date: 2026-04-28
- Productive Python code in `Backend/src`: 30 files and 5244 lines
- Backend tests are not part of this file, but the current snapshot is backed by calibration, gesture, config and websocket tests

## Module Metrics

| Scope | Files | Lines | Reading |
| --- | ---: | ---: | --- |
| `main.py` | 1 | 102 | App bootstrap, lifespan and shared websocket entry point |
| `api/` | 4 | 443 | Flat router package with config, runtime and calibration endpoints |
| `core/` | 4 | 215 | Config, DB bootstrap, logging and realtime hub |
| `repositories/` | 3 | 782 | Config and weather persistence, now including calibration storage |
| `schemas/` | 9 | 618 | Pydantic contracts including modality-generic calibration models |
| `services/` | 8 | 3083 | Gesture runtime, calibration coordination and other domain services |

## Current Logic Model

The backend remains a modular monolith. The major architectural step in this snapshot is that gesture tuning is no longer just static configuration. It is now a runtime capability:

- `services/gestures.py` still owns detection, cooldown and semantic action publication.
- `services/calibration.py` owns active calibration sessions, accepted sample capture, heuristic analysis, apply, rollback and discard.
- `repositories/config.py` persists both normal config and calibration artifacts.
- `api/system_endpoints.py` exposes the full calibration lifecycle over HTTP.
- `core/realtime.py` carries calibration feedback over the same websocket channel as the existing interaction events.

This keeps the stack coherent: no parallel storage, no parallel event channel and no one-off offline tuning path.

## Critical Assessment

- The backend structure is materially stronger because calibration was added as a first-class slice rather than a side script.
- The main hotspot is now shared between gesture runtime and calibration orchestration. The split is better than before, but input behavior is still the dominant complexity cluster.
- The modality-generic contracts are a deliberate investment for future voice calibration, but they also introduce some dormant surface area that is not implemented yet.
- Placeholder calendar and smart-home domains remain clearly behind the delivered maturity of the input stack.

## Intended But Missing Elements

- voice calibration implementation on top of the already generic session lifecycle
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