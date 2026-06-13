# Sprint 004 — Flight-plan compiler (the canonical merchant run)

Implements milestone **M3** from `planning/004-project-plan.md`.

## Goal

Turn a filed flight plan — a ship, an origin, ordered destination waypoints with
layovers, and a departure time — into a contiguous list of absolute-time
`Segment`s, and answer "where is the ship at time T?" by evaluating the segment
covering T. This is the inflection point where the pure math (Sprints 002–003)
becomes a stateful, multi-leg plan, and where `SimClock` becomes load-bearing.
The target is the project's original use case: a merchant departing Earth for
Titan Station, a 6-hour layover, and the return to Earth.

## Scope

- **Ephemeris extension** (per the Sprint 004 scope decision): add **moons**
  (Titan, orbiting Saturn) and **stations** (Titan Station, attached to a
  parent body) to the body registry, with a recursive `position(name, t)`
  resolver. A small `list-bodies` capability so destinations are discoverable
  (`where-is --list`).
- **Flight-plan compiler** in `hvsim/flightplan/`: `Ship` (accel/velocity caps),
  `Waypoint` (body + layover), `FlightPlan` (origin + ordered waypoints +
  departure), compiled into ordered `Segment`s with absolute `t_start`/`t_end`.
  Transit segments wrap a Sprint-003 `Trajectory` (moving-target intercept);
  layover segments hold the body the ship is docked at.
- **State query** `state_at(compiled, T)`: docked-at-origin before departure,
  the trajectory state during a transit, the body's position during a layover,
  docked-at-destination after arrival. Reports position, velocity, current
  phase, and the next ETA.
- **`SimClock` graduation**: rate / jump / advance helpers so a multi-hour plan
  can be filed with "depart now" (`clock.now()`) and fast-forwarded in tests.

## Out of scope

- **Persistence / SQLAlchemy / SQLite** — milestone M4. This sprint compiles to
  in-memory domain objects; the `Segment` shape is designed to map onto rows
  later, but no DB yet.
- **HTTP API** — also M4. Compiler + `state_at` are exercised directly in tests
  (and lightly via the `where-is` CLI for body positions).
- **Orbital-velocity realism** — transits still arrive at rest in the
  heliocentric frame, and a docked ship reports zero velocity (body velocity
  vectors remain deferred from Sprint 002). Position tracks the body correctly.
- **Moon orbital-plane fidelity** — Titan is modelled in the ecliptic plane with
  an approximate phase. Saturn's axial tilt and Titan's exact J2000 longitude
  are ignored; the effect is at Titan's orbit scale (~1.2e6 km), which is <0.1%
  of the Earth–Saturn distance and so negligible for *flight times* (the core
  value). This is a clock simulator, not a docking simulator.
- Route planning / multi-ship scheduling / abort semantics.

## Tasks

- [x] Refactor ephemeris so the Keplerian solve is reusable; add a `position`
      resolver that handles planet / moon / station by walking the parent chain.
- [x] Add Titan (planetocentric Keplerian, ecliptic-plane approximation) and
      Titan Station (attached to Titan) to the registry; `list_bodies()`.
- [x] `where-is` works for moons/stations; add a `--list` flag.
- [x] `SimClock`: `set_rate`, `jump_to`, `advance` (re-anchor so sim time stays
      continuous across a rate change).
- [x] `Ship`, `Waypoint`, `FlightPlan`, `Segment` domain objects.
- [x] `compile_plan(plan)` → contiguous absolute-time segments (transit +
      layover), using `solve_intercept` per leg.
- [x] `state_at(compiled, T)` → position/velocity/phase/ETA across all phases
      and the before/after-plan edges.
- [x] Tests (see acceptance criteria).

## Acceptance criteria

- **Titan Station resolves**: heliocentric distance ≈ Saturn's (9–10 AU), and
  within ~1.3e6 km of Saturn's centre (i.e. inside Titan's orbit).
- **Canonical use case compiles**: `Ship(250 g, 0.6c)`, origin Earth, waypoints
  `[Titan Station (6 h layover), Earth]`, departing a fixed instant →
  segments `transit, layover, transit`. The layover is **exactly 6 h**; each
  transit is ~half a day (order ~12–15 h); segments are contiguous
  (`t_end[i] == t_start[i+1]`) and absolute-time.
- **State across phases**: before departure → docked at Earth, zero velocity;
  mid-transit → moving, speed > 0, position on the chord; during layover →
  co-located with Titan Station, zero velocity; after the last segment →
  docked at Earth. Position is continuous across segment boundaries.
- **Depart-now via SimClock**: filing with `clock.now()` and querying
  `state_at(plan, clock.now())` agree; advancing the clock (rate or jump)
  deterministically moves the reported state along the plan.
- **Determinism**: identical inputs → identical compiled segments and states.
- All domain code remains importable/runnable with no service and no DB.

## Notes / decisions

- Milestone mapping: M3 is the *compiler*; persistence is M4. So `Segment` is an
  in-memory dataclass here, shaped to become a DB row later.
- Titan elements: a ≈ 1.22187e9 m, e ≈ 0.0288, period ≈ 15.945 d. Phase/plane
  simplified (see out-of-scope) — chosen for clock realism, not ephemeris
  precision.
- Listing: a `list_bodies()` + `where-is --list` is enough for now; the full
  `GET /bodies` endpoint is M4.

## Outcome — DONE

- Shipped on branch `sprint-004-flightplan`. 47 tests pass; ruff + format clean.
- **Canonical use case works end-to-end:** SS Harrington (250 g / 0.6c), Earth →
  Titan Station (6 h layover) → Earth departing 2026-01-01 compiles to
  transit (13.52 h) / layover (6.00 h) / transit (13.54 h) = **33.1 h** round
  trip, peaking at 0.199 c mid-transit.
- Ephemeris refactored into a body registry: `kepler._orbital_to_xyz` is now
  shared; `bodies.py` resolves planets/moons/stations recursively via
  `heliocentric_position`. Titan + Titan Station added; `list_bodies()` +
  `where-is --list`.
- `BODIES` now means *all* known bodies (was planets-only); the orbit-band test
  switched to `PLANET_NAMES`.
- `SimClock` graduated: `set_rate` / `jump_to` / `advance` re-anchor so sim time
  stays continuous across a rate change. "Depart now" = file with `clock.now()`.
- Segments are contiguous absolute-time; `state_at` covers predeparture →
  transit → layover → arrived, position continuous across boundaries.
- **Simplifications carried (as scoped):** docked ships report zero velocity
  (no body-velocity vectors yet); Titan modelled in the ecliptic plane with an
  approximate phase. Persistence + HTTP API remain M4.
