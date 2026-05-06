# Quality Metrics

This document describes the implemented repository-internal metrics system and the metric classes that are currently measured in the repo.

The design goal is still pragmatic: collect reproducible quality signals that are directly useful for engineering decisions, keep the artifact model simple, and avoid pretending that every measurable number should become a gate.

## Scope

The current implementation measures four slices:

- Backend: pytest, pytest-cov, mypy, flake8, radon
- Frontend: Vitest with coverage, vue-tsc, Vite build, ESLint
- Repo-wide duplication: jscpd
- Gesture subsystem: offline gesture benchmark based on the existing video corpus in `pics/`

All slices are aggregated into a shared JSON and Markdown summary under `reports/quality/`.

## Collected Metrics

### Backend

- Test count and pass/fail status
- Line and branch coverage
- Typecheck status
- Lint status and finding counts
- Cyclomatic complexity hotspots and rank distributions
- Maintainability index hotspots and distributions
- Halstead metrics
- Raw metrics, LOC, and largest-file summaries

### Frontend

- Test count and pass/fail status
- Line, statement, function, and branch coverage
- Typecheck status
- Build status
- ESLint errors and warnings

### Duplication

- Duplicated percentage
- Duplicated lines
- Clone count

### Gesture Slice

The gesture slice is intentionally different from the generic backend/frontend metrics. It reports domain-specific recognition-quality signals from the existing offline benchmark harness instead of more generic static-analysis numbers.

The aggregated gesture section currently contains:

- Corpus path and video count
- Overall video accuracy
- Per-gesture video accuracy
- Dominant confusion pairs derived from failed benchmark samples
- Negative swipe false-positive summary
- Negative push false-positive summary
- Sequence-shadow status and promotion-readiness context
- Recommendation excerpts from the benchmark output

## Artifacts

The pipeline produces these artifact groups:

- `reports/quality/backend/`
- `reports/quality/frontend/`
- `reports/quality/shared/`
- `reports/quality/gestures/`
- `reports/quality/summary.json`
- `reports/quality/summary.md`

The gesture artifact folder currently contains:

- `reports/quality/gestures/status.json`
- `reports/quality/gestures/gesture_benchmark.json`
- `reports/quality/gestures/gesture_benchmark.txt`

## Commands

Run the full pipeline:

```bash
npm run quality
```

Run individual slices:

```bash
npm run quality:backend
npm run quality:frontend
npm run quality:duplication
npm run quality:gesture
npm run quality:aggregate
```

## Gesture Phase 1 Policy

The gesture slice is Phase 1 and report-only by design.

This means:

- a broken benchmark execution is visible as a failed quality slice
- an accuracy miss is visible in the summary
- gesture accuracy does not participate in `quality:gates`
- sequence-promotion readiness is informational only
- negative false-positive findings are informational only

This is intentional. The current corpus is still too small and environment-specific to justify a stable CI gate.

## Hotspot Interpretation

The current hotspot list still comes from the generic backend/frontend aggregation and is meant to prioritize plausible engineering review areas, not to replace subsystem-specific analysis.

The backend summary now also exposes a richer report-only structure behind those hotspot headlines:

- flake8 finding counts, top codes, and affected files
- radon cyclomatic-complexity rank distributions and high-risk file concentration
- maintainability-index bands
- largest backend files from raw metrics for size-aware interpretation

Backend hotspots currently tend to cluster around:

- `Backend/src/services/gesture/runtime.py`
- `Backend/src/services/gesture/detection.py`
- `Backend/src/services/calibration.py`
- `Backend/src/repositories/config.py`
- `Backend/src/services/musical_audio.py`

Frontend hotspots currently tend to cluster around:

- `Frontend/nimrag-frontend/src/utils/interactionReducer.ts`
- `Frontend/nimrag-frontend/src/utils/layout.ts`
- `Frontend/nimrag-frontend/src/widgets/registry.ts`

## Explicitly Deferred Metrics

The following metric families are still intentionally excluded or deferred:

- SonarQube or SonarCloud
- Xenon or other additional hard complexity gates
- Branch coverage as a mandatory CI gate
- Repo-wide automation of CBO or LCOM4
- DIT and NOC
- Runtime reliability metrics such as MTBF or MTTR
- Live-camera gesture telemetry as part of the current CI slice
- Mutation testing, property-based testing, and profiler-driven optimization as part of gesture Phase 1

The reason is methodological fit. Some of these metrics require operational data that the repo does not collect yet, while others are valuable only after the smaller current slices are stable.

## Next Step

The next logical expansion is to continue strengthening backend code-metric interpretation without turning noisy signals into gates too early. The highest-yield additions are dead-code candidates, architecture and coupling proxies, and targeted smell detection around the existing gesture, calibration, and orchestration hotspots.