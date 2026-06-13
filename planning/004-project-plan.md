# Honorverse Simulator — Project Plan

*Drafted 2026-06-13 with Claude Code, building on the Copilot discussions in 001–003.*

## Vision

A real-time simulation of Honorverse-style space travel where the point is the
**realism of the clock**, not flashy graphics. You file a flight plan for a
merchant ship, and then — in actual wall-clock time — it spends twelve hours
crossing to Saturn, sits at Titan Station for its six-hour layover, and comes
home. Dashboards show where everything is *right now*. Eventually: more star
systems, hyperspace, wormholes, navies, and LLM-narrated wars.

## Guiding principles (from discussions 001–003, affirmed)

1. **The ship simulator stays dumb, deterministic, and math-driven.** It never
   invents anything, stores lore, or computes routes. It executes flight plans
   and answers "where is everything at time T" analytically.
2. **No game loop.** Flight plans are compiled into absolute-time segments at
   submission. State queries evaluate closed-form kinematics at the current
   timestamp. No drift, no background physics ticks, perfectly cacheable.
3. **Smart things live elsewhere.** Universe generation, route graphs, combat,
   and narrative are separate services added in later phases, each replaceable
   without touching the physics.
4. **Real time is the default, but the clock is a service.** A `SimClock`
   abstraction (epoch offset + rate multiplier, default rate 1.0) lets dev and
   tests fast-forward a three-day trip without waiting three days. Production
   runs at 1.0 — that's the whole point of the project.

## Decisions made

| Decision | Choice | Rationale |
|---|---|---|
| Language / framework | Python 3.12+, FastAPI | Fast iteration on math-heavy code; Pydantic models double as API schema |
| Persistence | SQLite | Zero-ops, tiny data volume; revisit Postgres when the universe-builder arrives |
| Physics | Newtonian kinematics with velocity cap | See "Relativity" note below |
| Ephemeris | Analytic Keplerian elements (JPL approximate planetary elements, J2000) | Deterministic, offline, accurate to arcminutes — no API dependency, real planet positions for today's date |
| Units | SI (m, s) internally; km / AU / human-readable durations in API responses | |
| Deployment | Docker container, docker-compose | Matches the multi-container future (combat sim, narrative engine) |

### Relativity note

At 250 g it takes **~44 AU of runway to reach 0.6c** — longer than any
plausible in-system run. Real Sol-system trips peak at 0.19–0.35 c, where time
dilation is a 2–6% effect. So: Newtonian math everywhere, and we *report*
cumulative shipboard time dilation as a flavor field in ship state
(`subjective_time_delta`). The 0.6c cap still matters for the math engine —
it just only engages on very long legs (and later, in other star systems).

### Correction to discussion 001

The Copilot example claimed Earth→Titan at 250 g "hits 0.6c before the halfway
point." It doesn't — not even close:

- 250 g = 2,452.5 m/s²; distance to reach 0.6c: v²/2a ≈ 6.6×10¹² m ≈ **44 AU**
- Earth→Saturn at ~1.28×10⁹ km is a pure brachistochrone (flip at midpoint):
  - t = 2·√(d/a) ≈ **12.7 hours**, peak velocity ≈ **0.187c** at the flip
- Even Earth→Neptune (~30 AU) only peaks at ~0.35c, taking ~24 hours.

So in-system trips are **hours to a day** — the "days and weeks" timescales
arrive with hyperspace travel between systems in Phase 2, which matches the
books. The trajectory solver must handle accel/coast/decel *and* the
no-coast brachistochrone case; in Sol, brachistochrone is the norm.

---

## Phase 1 — Ship simulator microservice (Sol, normal space)

### Scope

- Sol system: 8 planets + Luna + a handful of named stations (Titan Station,
  etc.) on Keplerian orbits; stations attach to a parent body.
- Ships with: name, class, max accel (g), max velocity (fraction of c).
- Flight plans as ordered waypoints with layovers; "depart now" or scheduled.
- Real-time state queries: position, velocity, acceleration, current segment,
  ETA, percent complete.

### Domain model

```
Body        id, name, kind (star|planet|moon|station), parent_id,
            keplerian elements (a, e, i, Ω, ω, M₀, epoch) or fixed offset
Ship        id, name, class, max_accel_g, max_velocity_c, status,
            home_body_id, current flight_plan_id (nullable)
FlightPlan  id, ship_id, status (scheduled|active|complete|aborted),
            created_at, departs_at, waypoints (ordered)
Waypoint    body_id, layover_duration
Segment     flight_plan_id, seq, kind (accel|coast|decel|layover|docked),
            t_start, t_end, r₀ (vec), v₀ (vec), a (vec)   ← all absolute time
```

Compiled `Segment` rows are the heart of the design: each is a closed-form
piece of trajectory, so `state(t)` is a binary search over segments plus one
kinematics evaluation.

### Trajectory solver

1. **Moving-target intercept.** The destination planet moves during a 12-hour
   trip. Solve by fixed-point iteration: compute trip time to the target's
   current position, re-evaluate target position at projected arrival, repeat
   (converges in 2–3 iterations since planet speed ≪ ship speed).
2. **Profile selection.** Given distance d, accel a, cap v_max:
   - If d < v_max²/a → brachistochrone (accel, flip, decel) — the common case in Sol
   - Else → accel to cap, coast, decel
3. **Arrival condition.** v1 ends the trajectory at the target's position with
   zero heliocentric velocity (planet orbital velocity ~10–30 km/s is noise
   against peak speeds of tens of thousands of km/s; matching it is a later
   refinement, noted as a known simplification).
4. Straight-line (chord) paths — no gravity, no orbital mechanics for the
   ship itself. That's faithful to impeller wedges anyway.

### API sketch

```
POST /ships                          create ship
GET  /ships                          list ships w/ summary state
GET  /ships/{id}                     ship + current state
GET  /ships/{id}/state?at=<ts>       full state vector (default: now)
POST /ships/{id}/flightplan          file & compile a plan
GET  /ships/{id}/flightplan          active plan w/ segment timeline & ETAs
DELETE /ships/{id}/flightplan        abort (v1: ship halts at computed point)
GET  /bodies                         all bodies w/ current positions (dashboard map)
GET  /bodies/{id}/state?at=<ts>      single body position
GET  /clock                          sim time, rate, epoch offset
PUT  /clock                          dev/test only — set rate or jump time
```

State response includes: position (km + AU), velocity (km/s + fraction of c),
acceleration (g), current segment + time remaining in it, overall ETA,
distance remaining, and `subjective_time_delta`.

### Stack & repo layout

- Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy + SQLite, pytest,
  `uv` for env/deps, ruff for lint/format, Dockerfile + compose.
- `src/hvsim/` → `ephemeris/`, `kinematics/`, `flightplan/`, `api/`, `clock/`
- Kinematics and ephemeris are pure functions — fully unit-testable without
  the service running.

### Milestones

1. **M1 — Ephemeris**: Keplerian propagation for planets; CLI that prints
   "where is Saturn right now"; tests against known positions.
2. **M2 — Trajectory math**: profile selection + moving-target solve as pure
   functions; tests for the worked examples above (Earth→Titan ≈ 12.7 h).
3. **M3 — Flight plan compiler**: waypoints → absolute-time segments; SimClock.
4. **M4 — API + persistence**: FastAPI service over SQLite; Docker; the
   original use case end-to-end (merchant, 250 g, Earth → Titan Station,
   6 h layover, return, depart now).
5. **M5 — First dashboard widget**: simplest possible 2D top-down Sol map
   polling `GET /bodies` + `GET /ships` (proves the API shape is right).

---

## Phase 2 — Universe builder, hyperspace, wormholes

Per discussion 002 — summary of intent, design deferred until Phase 1 ships:

- **Universe builder**: separate app + DB (likely the Postgres trigger point).
  Generates star systems (Manticore A/B, Yeltsin's Star…), planets, stations,
  the wormhole graph, hyperspace band metadata, and the known-routes graph.
- **Ship simulator additions**: new segment kinds only — `hyper_translate`,
  `hyper_cruise` (speed multiplier per band), `wormhole_queue`,
  `wormhole_transit`. The service still just executes segments it's handed.
- **Route planning lives in the universe builder** (or a thin nav service),
  not the physics engine.
- This is where **days-and-weeks travel times** appear: hyper passage
  Manticore→Yeltsin is days; without the Junction, far longer.

## Phase 3 — Navies, combat, narrative

Per discussion 003 — summary of intent:

- **Combat simulator**: separate container; fleets in, stats out (damage,
  casualties, munitions, events). Tabletop-wargame-style rounds. No tactics UI.
- **Narrative engine**: LLM turns combat results into after-action reports
  and in-universe dispatches.
- **Admiral agents**: per-polity LLM personas issuing orders that become
  flight plans for the existing simulator.

## Open questions (decide later, not blockers)

1. Station orbits: model Titan Station on Titan's actual orbit around Saturn,
   or park it at Saturn-barycenter + offset for v1?
    - For v1, park it.
2. Abort semantics: halt-in-place vs. auto-replan to nearest body.
    - Interesting for v1 especially as if the ship is in it's decel phase, while
      it can manuever, it may be difficult to reroute to nearest body (it has to
      dump all of it's velocity).
3. Fuel/reactor-mass tracking — Honorverse impellers don't burn reaction
   mass, so probably *never*, but bunker/maintenance clocks could gate ops tempo later.
4. Event push for dashboards (SSE/WebSocket) vs. pure polling for v1.
    - Pure polling for v1
5. Compensator failure / accel safety margins as flavor (merchants run at
   less than 100% military power) — could make `max_accel_g` a ceiling with
   a cruise setting.
    - Let's add the flavor. We'll need to extend the ship data or add a default
      chance of compensator failure over time. Could not find any "canon" data
      on this, but got the suggestion: "P(fail_per_hour) = k*( p - 0.8 )^3"
      where "p: fraction of max compensator load" and "k: tuning constant
      (suggested starting value 0.02)"
