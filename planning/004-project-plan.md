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

## Phase 1.5 — Operate & Observe

*Added 2026-06-13. Phase 1 built the simulator and proved it locally; Phase 1.5
**runs it for real and makes it observable** before the Phase 2 build-out. These
are operational/visualization milestones, not new physics.*

**Decisions (this planning session):**

- **Grafana feed = pull.** Prometheus (already on `kubsdb:9090`) scrapes a
  `/metrics` endpoint on the API. A scrape triggers an analytic state eval —
  **no background tick**, consistent with the "no game loop" principle. (Push /
  pushgateway was considered and declined for that reason.)
- **Two dashboards, both kept:** the standalone in-repo widget (M5) *and* a
  `kdeskdash` text-first mode (M9). They serve different audiences.
- **Deployed instance runs real time** (rate 1.0, `HVSIM_DEV_CLOCK` unset) — the
  whole point is watching real clocks tick. Dev/test keeps the clock controls.

### M6 — Deploy to `kubsdb`

Containerized service running on `kubsdb`, reachable on the LAN at
`http://kubsdb:4667`, with a `justfile` at the repo root.

- `justfile` recipes: `deploy`, `health`, plus `logs` / `down` / `seed`.
- Image delivery — **decision at sprint start**: simplest homelab path is
  `docker save | ssh kubsdb docker load` (no registry); alternative is
  `ghcr.io/kenhia/hv-simulator`. Lean save/load for v1.
- Persistent SQLite on a named volume (survives restarts). Real-time clock,
  dev clock **off**. Open `kubsdb` firewall for 4667 if needed.
- Done when `just health` (against `kubsdb`) returns ok and the canonical run
  works over the LAN.

### M7 — Live shakedown (short real-time trips)

File 2-3 ships with flight plans that **complete in 1-4 hours of wall-clock
time**, so we observe completed trips before committing to multi-day flights.

- A `seed` recipe/script files the ships against the deployed instance.
- Destinations chosen by *current* geometry to land in the 1-4 h window
  (inner-planet hops, e.g. Earth↔Venus/Mars depending on the date). **Optional:**
  add Luna (deferred from Sprint 002) for ~15-minute demo loops.
- Observe to completion (status `arrived`); record a short results note.
- Validates real-time pacing, persistence across the trip, and that state stays
  correct end-to-end on the real deployment.

### M8 — Prometheus `/metrics` + Grafana "Ship Status"

- **`/metrics` endpoint** (pull) via `prometheus_client`. Per-ship gauges
  labelled by ship id/name/phase/destination: speed (km/s and fraction c),
  distance-to-destination, percent-complete, ETA (unix ts); plus ship counts by
  phase. The scrape computes current state — no loop.
- Prometheus scrape config for the new target; **30 s interval** (positions
  change over hours; finer is wasteful).
- Grafana **"Ship Status"** dashboard on the existing deployment
  (`kubsdb:3000`): a ships-in-flight table (phase, speed, %-complete, ETA) and a
  couple of time-series (speed, distance remaining). Dashboard JSON lives in the
  repo (`grafana/`), provisioned via `ansible-k` (or manual import for v1).
- **Side task — Grafana deployment reference:** extract the key facts (URL,
  datasource UID/name, how dashboards are provisioned) from
  `~/src/config-src/ansible-k/` into a durable reference, so future work doesn't
  re-read the ansible each time.

### M9 — `kdeskdash` handoff

A handoff document enabling a new **text-first** mode in `~/src/tools/kdeskdash`
(sibling dashboard to `~/src/tools/kpidash`): ships in flight with location,
speed, phase, ETA.

- Contents: API base URL, the endpoints + JSON shapes a mode needs
  (`GET /ships`, `GET /ships/{id}/state`, `GET /bodies`), suggested polling
  cadence, and a sketch of the first text layout.
- The mode itself is built in the `kdeskdash` repo (separate), guided by this doc.

### M5 (Phase 1) — standalone Sol-map widget

Still wanted (kept per this session). The simplest 2D top-down Sol map polling
`GET /bodies` + `GET /ships`. Low-dependency; can slot in anytime — a good quick
win, independent of M6-M9.

### Sequencing

M6 → M7 unblock everything (a live target to point at). M8 needs M6 (deployed)
+ a small code change (`/metrics`). M9 is a doc, doable once the API shape is
stable (now). M5 is independent. Suggested order: **M6, M7, M8, M9**, with M5
slotted whenever. Each becomes its own sprint spec under `sprints/` when started.

---

## Phase 2 — Galaxy (re-founded engine)

*Design detail in `005-honorverse-data-review.md` (the dataset) and
`006-galaxy-architecture-brainstorm.md` (architecture + decisions, 2026-06-14).
This section is the sprint-triggering breakdown.*

**Goal:** a navigable multi-system galaxy with the same "realism of the clock,"
reached by re-founding the engine on a **lazy deterministic discrete-event
simulation (DES)** — the wormhole queue makes a ship's transit time
unknowable-until-arrival, which pure precompute can't express. Segments stay
closed-form; some boundaries are *events* resolved by stateful *resolvers*
(wormhole queue first, combat later); `state(T)` = deterministic replay to T
(no game loop, still zero-drift, reproducible).

**Cross-cutting decisions (from 006):**

- **Engine model:** lazy deterministic DES; **DES-core-first** (2a/2b build on
  it, no retrofit). `ephemeris`/`kinematics` port; flight-plan/execution rebuilt.
- **Language:** stay **Python**; freeze boundary contracts so a later
  *engine-only* Rust port is cheap. Formal port-decision checkpoint at 2c.
- **Data:** authored **JSON is source of truth** (git-reviewable, canon-flagged,
  CC BY-SA); a **universe-compiler** emits a read-only **SQLite "universe
  artifact"** the engine loads. Engine never touches loose JSON.
- **Repo:** monorepo — `engine/ tools/<name>/ data/ ui/` + `justfile`;
  **`data/` keeps its own CC BY-SA 3.0 license** (per-directory; code stays MIT).
- **Epoch:** sim starts **1890 PD** (peacetime); advances toward ~1905 PD when
  combat lands. **`ALLOW_ANACHRONISMS`** flag gates temporal validity
  (`valid_from`/`valid_to`): default `true` pre-combat, `false` once combat
  lands, always settable (the original *Fearless* can still fly).
- **Separation preserved:** the **nav route planner computes routes** (tools/data
  side); the **engine only executes** a filed route and never invents lore.

### Phase 2.0 — Contracts & monorepo foundation  ⬅ next sprint

The load-bearing seam. Freeze it before building on it.

- Monorepo restructure (`engine/ tools/<name>/ data/ ui/`, per-tool
  `pyproject.toml`, workspace `justfile`); `data/` carries CC BY-SA + attribution.
- **Contract 1 — universe-artifact schema** (the compiled SQLite shape: systems,
  stars/binary, bodies+orbits, places, belts, wormhole graph, hyperspace bands,
  hyper-limit table, ship classes; FK-resolved, id-namespaced).
- **Contract 2 — engine HTTP API** (OpenAPI): file ships/routes, query state
  across systems, junction/queue state, clock.
- Migrate the scribe skills into `tools/`; land the dataset JSON under `data/`.
- **Deliverable:** agreed, versioned contracts + skeleton monorepo + build
  orchestration. (This is the sprint we start with.)

### Phase 2a — Universe foundation

- **universe-compiler** tool: JSON → validate (schema) → resolve FKs → namespace
  ids (the Sol/Manticore `titan` collision) → read-only SQLite artifact.
- **coordinate-frame solver** (Sol-origin, +Z galactic north; triangulate canon
  bearings/distances) — `canon:false`. Engine prefers canon pairwise distances
  when present, frame-derived otherwise.
- **orbit-derivation** tool (Kepler from canon anchors: Manticore 1.73 T-yr, etc.).
- **Engine:** DES core skeleton; load the universe artifact; `ephemeris` extended
  to **per-system + binary primaries**; report body positions galaxy-wide at T.
- **Deliverable:** engine loads the compiled multi-system universe and answers
  "where is body X in system Y at T," including binary Manticore-A/B.
- *Delivered across Sprints 010 (compiler + orbits + binary ephemeris) and 011
  (coordinate frame + wormhole/hyperspace compiled in + engine exposure).*

### Phase 2a.1 — Expand the galaxy (pipeline integration)

**Lean: grow the galaxy *while* we verify** — prove the data→artifact→engine
pipeline handles real expansion by adding real systems, not a throwaway smoke
test. The verification *is* useful content.

- **Add two gateway systems via the scribes:** **Beowulf (`sigma-draconis`)** —
  the Sol→Manticore on-ramp, the single highest-value system per the data team's
  `001` — and **Trevor's Star** (San Martin; Manticore member, directly linked).
  Both currently exist only as stubbed wormhole termini; building them resolves
  the stubs into real systems.
- **Add ships + at least one new ship class** (a navy/class not yet in the set).
- **Run the full pipeline end-to-end:** scribe scrape → `orbit-derive` → `frame`
  → `compile-data` → engine. The acceptance criteria *are* the integration
  assertions: each new system places in-frame, its bodies are placeable, its
  wormhole link to Manticore is present, and the new class + ships compile and
  appear via `/systems`, `/wormholes`, and the fleet.
- **Codify the workflow LAST:** after running the expansion once manually
  (capturing the real sequence + rough edges), write an **`expand-galaxy`
  orchestrator skill** — a runner/checklist that sequences the scribe step(s)
  then the deterministic tool pipeline (derive → frame → compile → verify).
  Build it from the proven flow, not a guessed one; the scribes keep the
  canon-vs-fabricated judgment.
- *Sprint 012.* Still no travel (that's 2b).

### Phase 2b — Inter-system travel (no queue yet)

- **Nav route planner** (graph search over systems + wormhole edges + hyper
  lanes) → a filed multi-mode route.
- **Engine executes multi-mode plans on the DES core:** n-space accel/coast/decel
  (the **coast phase finally fires** on binary/interstellar legs), `hyper_cruise`
  (band apparent-velocity + hyper-limit, read from data), `wormhole_transit` as
  instant + fixed safety buffer (no dynamic queue yet).
- **Deliverable:** end-to-end **Sol → Manticore → Yeltsin's Star** flight plan
  with realistic multi-day clocks; state queryable across systems. (Manticore↔
  Yeltsin's is canon-31-ly and flyable without the full frame.)

**Routing realism — obstacle clearance (noted 2026-06-15).** Two geometry cases:

- *Clearing the hyper limit.* A ship inside the limit flies an n-space leg out
  past it before translating up, and drops back down at the destination's limit
  (you translate **only outside** the limit — you don't cross one while in hyper).
  The tempting "dogleg / curve around the limit ring to aim at the destination"
  is **not needed**: the limit (~2.6 AU for a G star) is a negligible point at
  interstellar (ly) scale, so the optimum is simply *clear the nearest limit
  crossing, then straight-line hyper.* The planner only needs the short
  climb-to-limit leg — no two-route comparison. **Will implement** (the climb leg).
- *In-system star avoidance.* The straight-chord solver can route a trip
  *through the primary* when origin and destination are near-opposite as seen
  from the star (a "corona flyby"). Real but rare. Fix = detect chord-vs-star
  within a safety/corona radius and dogleg via an offset waypoint. **Edge case:**
  implement when it bites; until then a known simplification (chords may clip the
  star on near-opposition trips). Note this already exists latently in the Phase 1
  Sol solver.

### Phase 2c — Wormhole queues (the DES payoff)

- **Wormhole queue resolver:** the dataset's `transit_model`
  (`tau(M)=A√M+B·M²`) + safety buffer + queue semantics; the "wait in queue"
  segment is **open-ended** until the resolver fixes the departure time.
- **Phantom traffic** (seeded, deterministic per junction) so queues feel alive
  without thousands of tracked ships.
- **Deliverable:** "SS Tankersley is #3 in the queue, transit in 12:27 … #2 …
  #1 … *pops to Basilisk*." The engine is now a true simulator.
- **Checkpoint:** formal **Rust-port decision** for the engine (likely "not yet,"
  but the review point).

### Phase 2.5 — First-class UI

- **Galaxy/map view** (systems as nodes, wormhole edges, ships in transit) that
  **drills into a per-system top-down** (today's Sol map, generalized).
- **Switch systems, zoom, layer toggles** (kwi #57 generalizes here), **queue/ETA
  panels** at junctions, **time controls**. Separate front-end on the engine API;
  richer web stack than vanilla Canvas is fair game. Dead-reckoning still applies.
- **Deliverable:** a first-class way to navigate the galaxy and watch ships/queues.

### Deferred within Phase 2 (confirmed safe to skip for a navigable galaxy)

Gravity waves, the Tellerman wave, Warshawski sail-riding, dimensional shear
beyond the hyper-limit rule — these change *optimal* routing/speed ("fast lanes /
weather") but aren't required. Revisit post-Phase-2.

## Phase 3 — Navies, combat, narrative

Per discussion 003 — summary of intent. Combat is the **next DES resolver** after
the wormhole queue (battles resolve at an event time; results feed back as state).
This is where the sim **advances toward ~1905 PD** and `ALLOW_ANACHRONISMS`
default flips to `false` (era-correct fleets, still overridable).

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
