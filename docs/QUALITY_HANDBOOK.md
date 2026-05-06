# Quality Handbook

## Purpose

This document is the short operational companion to the broader metrics write-up in `docs/QUALITY_METRICS.md`.

Its job is to document the quality system exactly as it is implemented in the repository today:

- which commands exist
- which artifacts are generated
- which thresholds are informative only
- which checks currently block CI
- why the current gate set is intentionally conservative

## Source Of Truth

The implementation is controlled by these files:

- `package.json`
- `scripts/run_quality.js`
- `scripts/collect_quality_metrics.js`
- `scripts/check_quality_gates.js`
- `scripts/quality_thresholds.json`
- `.github/workflows/quality-metrics.yml`

If this handbook and the implementation ever disagree, treat the implementation files above as authoritative and update this document.

## Commands

Run the full report pipeline:

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

Run the cautious Phase 2 CI gates against the generated summary:

```bash
npm run quality:gates
```

## Generated Artifacts

The pipeline writes raw and aggregated outputs into `reports/quality/`:

- `reports/quality/backend/`
- `reports/quality/frontend/`
- `reports/quality/gestures/`
- `reports/quality/shared/`
- `reports/quality/summary.json`
- `reports/quality/summary.md`

The gate step reads `reports/quality/summary.json` rather than recomputing metrics itself. That keeps reporting and CI evaluation aligned on the same inputs.

## Current Metric Policy

The repository is now in `phase-2-cautious-gates` mode.

There are still two classes of quality signals:

1. Reported metrics that help identify hotspots and regression risk.
2. A small set of CI gates that are stable enough to block merges.

### Reported Thresholds

These values are kept in `scripts/quality_thresholds.json` and remain useful for summaries and interpretation even when they are not all hard gates:

- Backend line coverage target: `70`
- Backend branch coverage is collected and reported, but remains report-only
- Frontend line coverage target: `70`
- Frontend complexity warning threshold: `> 10`
- Backend preferred maintainability rank: `B`
- Duplication target max percent: `5`

These values are intentionally not all enforced as hard failures yet.

### Gesture Phase 1 Report-Only Signals

The gesture slice is currently a dedicated report-only slice.

It reports:

- corpus path and video count
- overall and per-gesture video accuracy
- dominant confusion pairs
- negative swipe and push false-positive summaries
- sequence-shadow status
- recommendation excerpts from the benchmark output

The slice execution itself must still succeed so the repository does not silently lose observability, but gesture accuracy and sequence-readiness are not part of CI gate enforcement in this phase.

## Current CI Gates

The current gate set is intentionally narrow.

CI fails when any of the following conditions is violated:

- Backend required steps: `pytest`, `mypy`, `flake8`
- Frontend required steps: `vitest`, `typecheck`, `build`, `eslint`
- Duplication required step: `jscpd`
- Backend line coverage must be at least `75%`
- Frontend ESLint errors must be at most `0`
- Duplication must be at most `5%`

### Explicit Non-Gates In Phase 2

The following signals are still report-only by design:

- Backend branch coverage
- Gesture benchmark accuracy
- Gesture sequence-promotion readiness
- Gesture negative false-positive findings
- Frontend coverage
- Frontend ESLint warnings
- Frontend complexity warnings
- Backend radon complexity and maintainability findings
- Hotspot ordering in the summary

## Rationale For The Current Gate Set

The current policy follows one rule: gate only on signals that are already stable enough to be trusted on every run.

### Why Backend Coverage Is Gated

Backend line coverage is already above the gate floor and is produced from a relatively stable test slice. A `75%` minimum is strict enough to prevent silent erosion while still leaving headroom for normal refactoring.

### Why Backend Branch Coverage Is Not Gated Yet

Backend branch coverage is now measured so missing decision-path coverage is visible in the shared summary, but it is still more volatile than the line-coverage baseline and needs a longer period of observation before it becomes a trustworthy CI boundary.

### Why Frontend Coverage Is Not Gated Yet

The current frontend coverage baseline is still too low for a safe hard gate. Enforcing an aggressive threshold now would mostly create churn and incentivize gaming the number instead of improving the weak areas deliberately.

### Why ESLint Errors Gate But Warnings Do Not

Zero frontend ESLint errors is a clean, binary contract. Warnings are still informative, but they currently contain too much style and complexity noise to serve as a reliable merge boundary.

### Why Duplication Is Gated

Duplication is cheap to measure, repo-wide, and already comfortably below the threshold. Keeping the gate at `5%` protects against obvious copy-paste regression without forcing premature architectural rewrites.

### Why Radon Metrics Are Still Report-Only

Complexity and maintainability findings are useful for triage, but they still need engineering judgment. They are better used to prioritize refactoring hotspots than to fail CI globally.

### Why Gesture Metrics Are Report-Only In Phase 1

The gesture benchmark is useful today because it turns the existing video corpus into a repeatable engineering signal. It is not trustworthy enough for CI gating yet because the corpus is still relatively small, environment-specific, and better suited to directional review than to a universal pass/fail contract.

## Current Verified Baseline

Validated on `2026-05-06` with `npm run quality:gates`:

- Backend coverage: `79.15%`
- Backend branch coverage: `55.60%` report-only
- Frontend ESLint errors: `0`
- Duplication: `1.75%`

This baseline is not itself a contract. It is only a reference point for future threshold discussions.

## How To Evolve The System

When changing the quality policy, keep the sequence explicit:

1. Refresh reports with `npm run quality`.
2. Inspect `reports/quality/summary.json`.
3. Adjust `scripts/quality_thresholds.json` only after confirming the current baseline is real.
4. Keep `scripts/check_quality_gates.js` limited to stable, low-noise checks.
5. Re-run `npm run quality:gates` after every policy change.

The intended next tightening step is not “gate everything”. The intended next step is to add one more low-noise gate at a time, only when the baseline is consistently healthy.