# Sprint 002 — Ephemeris (where is Saturn right now?)

Implements milestone **M1** from `planning/004-project-plan.md`.

## Goal

Given a date, compute the heliocentric position of any Sol planet from analytic
Keplerian elements — and prove it against known almanac positions — so later
sprints have real, deterministic targets to fly to.

## Scope

- Pure-function Keplerian propagation in `hvsim/ephemeris/`: given orbital
  elements + a time, return a 3D heliocentric position (SI metres, J2000 frame).
- The JPL "approximate positions of the planets" element set (8 planets) as
  static data in the package.
- Kepler's-equation solver (Newton iteration) for eccentric anomaly.
- A small CLI / script: `where-is <planet> [--at <iso8601>]` printing position
  in AU and km, defaulting to now (via `SimClock`, even if the clock is minimal
  for now).

## Out of scope

- Moons and stations (Luna, Titan Station) — added when the flight-plan sprint
  needs them; planets are enough to validate the math.
- Planet *velocity* vectors — position only this sprint, unless trivially free
  from the same elements (note it if added).
- The trajectory solver / moving-target intercept (Sprint 003).
- Any HTTP API — CLI only here.

## Tasks

- [x] Add the JPL approximate orbital elements (a, e, i, Ω, ϖ, L and their
      per-century rates, J2000 epoch) as a typed data table.
- [x] Implement element-at-time → mean anomaly → eccentric anomaly (Newton solve)
      → true anomaly → heliocentric ecliptic XYZ, returning SI metres.
- [x] Decide and document the output frame (J2000 ecliptic) and units in a
      module docstring.
- [x] Minimal `SimClock` (epoch + rate, default real-time) so "now" goes through
      one source even at this stage.
- [x] `where-is` CLI entry point.
- [x] Tests: validate Earth, Mars, Saturn positions at known dates against
      published almanac/Horizons values within a stated tolerance.

## Acceptance criteria

- `uv run pytest` includes ephemeris tests that pass within tolerance
  (target: within ~0.01 AU of a Horizons/almanac reference for the test dates —
  tighten if easily achievable).
- `where-is saturn` prints a plausible current heliocentric distance
  (~9.0–10.1 AU depending on date) in both AU and km.
- `where-is mars --at 2030-01-01T00:00:00Z` is reproducible (same input →
  identical output; no network, no wall-clock dependence beyond the `--at`).
- Ephemeris functions are importable and callable with **no** service running.

## Notes / decisions

- Reference for elements + algorithm: JPL "Keplerian Elements for Approximate
  Positions of the Major Planets" (Standish). Cite the exact table used in the
  module docstring.
- Tolerance is a *test* concern; the approximate-element model is good to
  arcminutes over 1800–2050, which is far better than the simulator needs.

## Outcome — DONE

- Shipped on branch `sprint-002-ephemeris`. 17 tests pass; ruff + format clean.
- Used the JPL 1800–2050 element set (`elements.py`); propagation in
  `kepler.py` returns heliocentric ecliptic-J2000 position in SI metres.
- Validated against **real JPL Horizons** state vectors (fetched 2026-06-13,
  hardcoded with provenance in `test_ephemeris.py`). Measured residuals:
  Earth 5e-6 AU, Mars 3e-4 AU, **Saturn 0.0125 AU (~4.5′)** — the latter is the
  expected accuracy of linear-rate elements for a giant planet (un-modelled
  Jupiter–Saturn perturbation), not a bug. Tolerances are therefore per-body:
  0.005 AU inner/Mars, 0.02 AU giants. The flat "~0.01 AU" target in the
  acceptance criteria was too tight for Saturn; per-body is the honest call.
- Time handling: input treated as UTC; TDB-UTC (~69 s ≈ 1e-5 AU) ignored.
- `where-is saturn` and `where-is mars --at 2030-01-01T00:00:00Z` both work and
  the latter is reproducible (acceptance criteria met).
- **Deferred to a later sprint:** planet velocity vectors, moons/stations.
