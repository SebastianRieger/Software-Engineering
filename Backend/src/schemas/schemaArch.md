# Schema Module Architecture Analysis

## Scope

- Snapshot basis: 9 files and 618 lines in `Backend/src/schemas`
- Domain schema files now include configuration, gestures, interactions, calibration, led, system, voice and weather

## Structure And Logic

The schema layer now models two levels of input behavior:

- static and runtime-facing contracts such as gesture config, gesture events and semantic UI actions
- session-oriented calibration contracts such as target definitions, collected samples, progress, analysis results, apply and rollback responses

The important architectural step is that calibration is modeled generically enough for a later second modality while staying concrete for the current gesture implementation. The lifecycle contracts are modality-neutral, while sample payloads, candidate config snapshots and now explicit reviewable config-patch contracts still carry gesture-specific fields where needed.

`schemas/gestures.py` now carries a deliberately broad `GestureConfig` contract. It no longer models only coarse gesture thresholds, but also the runtime and offline tuning surfaces that actually steer gesture decisions: push-pose heuristics, offline cycle-segmentation gates, primitive pass thresholds, resolver weights, candidate-shape constraints and runtime lifecycle grace windows.

## Critical Assessment

- The schema layer remains compact relative to the backend size even after adding calibration.
- Manual synchronization with the frontend TypeScript mirrors is now more expensive because calibration introduced a broader contract surface.
- The generic calibration contracts are appropriate, but they also create intentional dormant space for voice support that is not implemented yet.
- Gesture and calibration schemas together now represent one of the richest contract areas in the backend, which matches the delivered feature depth.
- The richer gesture config makes backend and tuner behavior more consistent, but it also raises the importance of disciplined documentation because frontend mirrors and manual API usage now face a wider contract surface.

## Intended But Missing Elements

- shared or generated contracts between backend and frontend
- real voice-calibration payloads on top of the already generic lifecycle types
- clearer contract versioning once calibration history and profiles evolve further

## Navigation

- Parent: `../backendArch.md`