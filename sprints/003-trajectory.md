# Sprint 003 — Trajectory math (the moving-target intercept)

Implements milestone **M2** from `planning/004-project-plan.md`.

## Goal

Given a start point, a destination **body**, a departure time, a max
acceleration, and a velocity cap, compute the trajectory that flies there —
solving the brachistochrone / accel–coast–decel profile *and* the fact that the
destination is moving during the trip. Pure functions; this is the first sprint
that consumes the `ephemeris` module.

## Scope

- A **1-D profile solver** in `hvsim/kinematics/`: given chord distance `d`,
  max accel `a`, and velocity cap `v_max`, return the motion profile —
  brachistochrone (accel, flip, decel) when `d < v_max²/a`, else
  accel–coast–decel. Reports phase durations, total time, and peak velocity.
- A **3-D trajectory** along the straight chord between two fixed points:
  apply the 1-D profile along `unit(r₁ - r₀)`, exposing position/velocity/accel
  at any elapsed time `t` (closed form).
- A **moving-target intercept**: given departure time `t₀`, a start position,
  and a destination body, fixed-point iterate on arrival time — estimate trip
  time to the target's position now, re-evaluate the target's position at the
  projected arrival, repeat until the arrival time converges.
- A minimal 3-vector helper (or stdlib tuples + small funcs) shared with later
  sprints — keep it boring.

## Out of scope

- **Flight-plan compilation** into stored `Segment` rows, waypoints, layovers,
  multi-leg trips — that's Sprint 004 (M3). This sprint is the solver those
  segments will be built from, exercised directly in tests.
- **Arrival velocity matching** — v1 arrives at the target's position with zero
  *heliocentric* velocity (planet orbital velocity ~10–30 km/s is noise against
  peak speeds of tens of thousands of km/s). Documented simplification.
- **Relativity** — Newtonian only; `subjective_time_delta` is reported later,
  not simulated here.
- Any HTTP API, persistence, or `SimClock` changes.
- Gravity / curved paths — straight chords only (faithful to impeller wedges).

## Tasks

- [x] 1-D profile solver: profile selection (`d < v_max²/a` → brachistochrone),
      phase durations, total time, peak velocity. Pure function.
- [x] Closed-form state-at-elapsed-time for a 1-D profile (distance, speed,
      accel at any `t` in `[0, total]`).
- [x] 3-D chord trajectory: wrap the 1-D profile along `unit(r₁ - r₀)`; expose
      `state(t)` returning position/velocity/acceleration vectors (SI).
- [x] Moving-target intercept via fixed-point iteration on arrival time;
      return the solved trajectory + arrival time. Document convergence
      (expected 2–3 iterations; cap iterations and assert convergence).
- [x] Velocity cap enforcement: speed never exceeds `v_max` in any profile.
- [x] Tests for the worked examples + invariants (see acceptance criteria).
- [x] Keep `kinematics` import-clean and pure (no service, no clock, no I/O).

## Acceptance criteria

- **Earth→Saturn brachistochrone** at 250 g (a = 2452.5 m/s²), cap 0.6c, using a
  representative Earth/Saturn separation (~8.5 AU): total time ≈ **12.7 h** and
  peak velocity ≈ **0.187 c**, matching the closed forms
  `t = 2·√(d/a)` and `v_peak = √(a·d)` to within ~1%.
- **Profile selection**: for `d < v_max²/a` the solver returns a two-phase
  brachistochrone (accel time == decel time, flip at the midpoint); for a
  synthetic `d > v_max²/a` (~> 88 AU at these settings) it returns three phases
  with a coast at exactly `v_max`.
- **Velocity cap**: across a swept set of distances, `max speed ≤ v_max` always,
  and equals `v_max` during any coast phase.
- **Moving-target intercept**: arrival position equals the destination body's
  ephemeris position at the *solved* arrival time to high precision (e.g.
  < 1000 km), and the fixed-point loop converges within the iteration cap.
- **Continuity / determinism**: `state(t)` is continuous in position and
  velocity across phase boundaries (no jumps), and identical inputs give
  identical outputs.
- `kinematics` functions are importable and runnable with no service.

## Notes / decisions

- Worked numbers (from `004`): 250 g, d = 1.28×10¹² m → `t = 2·√(d/a)` ≈ 45.7 ks
  ≈ 12.7 h, `v_peak = √(a·d)` ≈ 5.6×10⁷ m/s ≈ 0.187 c. The cap engages only when
  the brachistochrone peak would exceed `v_max`, i.e. `d > v_max²/a` ≈ 88 AU —
  so in Sol the brachistochrone never coasts; the coast path is tested
  synthetically and waits for hyperspace/interstellar distances to matter.
- Intercept start point: accept an explicit position vector (so a ship can
  depart from a body's current position via `ephemeris`); flight-plan wiring of
  "depart from body X" is Sprint 004's job.
- Decide where the 3-vector type lives (e.g. `hvsim/kinematics/vector.py` or a
  shared `hvsim/_vec.py`); whatever later sprints (`flightplan`, `api`) import.

## Outcome — DONE

- Shipped on branch `sprint-003-trajectory`. 34 tests pass; ruff + format clean.
- `Vec3` lives in `kinematics/vector.py` (per Ken's preference); `flightplan`/
  `api` will import it from there.
- Modules: `vector.py` (Vec3), `profile.py` (1-D `solve_profile` + closed-form
  `state(t)`), `trajectory.py` (3-D `Trajectory` + `solve_intercept`),
  `constants.py` (c, standard g).
- Verified end-to-end: Earth→Saturn on 2026-01-01 solves in **2 iterations** to
  a **13.5 h** brachistochrone peaking at **0.199 c**; Saturn drifts ~470,000 km
  during the trip and the intercept leads it (static aim would miss).
- Brachistochrone identities `t = 2√(d/a)`, `v_peak = √(a·d)` hold to ~1e-12;
  coast path verified synthetically past ~88 AU (never engages in Sol).
- **Simplifications (as scoped):** arrives at rest in the heliocentric frame (no
  orbital-velocity match); Newtonian only. Both deferred per the plan.
