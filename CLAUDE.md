# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Early development, executed sprint by sprint. Done so far: project skeleton
(Sprint 001); `ephemeris` (Sprint 002 — analytic positions + `where-is` CLI,
extended in Sprint 004 with moons/stations and a recursive body resolver);
`kinematics` (Sprint 003 — `Vec3`, the brachistochrone/coast solver, moving-
target intercept); and `flightplan` (Sprint 004 — `compile_plan` turns a filed
plan into absolute-time segments, `state_at` queries them analytically); and
`api` (Sprint 005 — FastAPI + SQLite + Docker: file a ship & plan over HTTP,
query state in real time). **Phase 1 is complete** — the canonical use case
(Earth → Titan Station → Earth) runs end-to-end as a service. **Phase 1.5
(Operate & Observe) is in progress**: deployed to `kubsdb` via the `justfile`
(M6); a Prometheus `/metrics` endpoint + Grafana "Ship Status" dashboard (M8).
Remaining: M7 live shakedown and M9 (`kdeskdash` handoff). **Phase 2 (galaxy) is
underway**: 2.0 froze the monorepo + boundary contracts; 2a (Sprints 010–011) added
the `universe-compiler` + `orbit-derive` + `coordinate-frame` tools and made the
engine load the compiled SQLite **universe artifact** — placing bodies (binary-aware)
in any system, the wormhole route graph + hyperspace model, and a Sol-origin galactic
frame. 2a.1 (Sprint 012) proved the pipeline on real expansion (Beowulf, Trevor's
Star, the Solarian Nevada class), stood up `docs/galaxy-changelog.md`, and codified
the `expand-galaxy` orchestrator skill. **Phase 2b is complete** (Sprints 013–016):
the engine was re-founded on a lazy discrete-event core (DES, Phase 1 parity), then
gained inter-system travel (hyper + wormhole), the canon hyperspace band model, and
the `tools/nav-planner` route-finder — a ship can now be auto-routed and flown
across the galaxy with realistic multi-day clocks (`just plan`). **Phase 2b.1
(operate the galaxy) is complete** (Sprints 017–018): canonical transponder ship
identity, and the `/fleet` HTTP API to file/fly/board planned routes — **deployed
to `kubsdb`** and validated with a live 5-ship shakedown. **Phase 2c is underway**:
Sprint 019 landed the engine's **first stateful resolver** — wormhole transit
**queues**. A ship reaching a junction joins a queue (an open-ended
`wormhole_queue` segment the fleet resolver fixes at arrival) and reports `queued`
with a counting-down position + ETA (`just queue-demo`); depth comes from a
seeded per-junction phantom-traffic knob (`traffic_intensity`, contract v0.4.0)
plus deterministic real-ship interleaving. Sprint 020 brought the queue to the
**deployed** service: it resolves the whole active fleet together (real-ship
interleaving on the board), surfaces `queue_position` on `/fleet`, implements the
contracted `GET /junctions/{id}/queue` (the "you are #3" board — real ships +
phantom, `just queue-board`), and emits per-junction queue-depth/wait metrics for
Prometheus/Grafana. Design is in `planning/006`. **Phase 2.5 (first-class UI) is
underway** (`planning/007`): a SvelteKit (Svelte 5) + Canvas-2D map app in `ui/`.
Sprint 021 landed the foundation + **galaxy graph** — placed systems as nodes in
the galactic frame, wormhole links as edges, pan/zoom, click → Side Data Panel,
At-a-glance + legend. Sprint 022 added the **LOD spine**: double-click / `Enter` /
zoom-in drills from the galaxy graph into a **per-system heliocentric top-down**
(star, planets/moons at live positions, hyper-limit ring, ride-on stations);
`Esc`/zoom-out leaves; a growing breadcrumb (`Galaxy → Sol → Sol / Earth`), zone
mode (`z`), fit (`f`), and a reserved `keymap`. Engine gained `GET /systems/{id}`
(hyper limit + stars + binary), `GET /systems/{id}/places`, and a Sol-bodies
delegate (Sol's JPL planets via `/systems/sol/bodies`). Sprint 023 made it **live**:
a sim-clock model + dead-reckoning render loop (rAF) animates ships on both scenes
(galactic motes in hyper, in-system dots with heading vectors), a **Fleet Board**
rail (collapsible, search, click-to-fly) shows the roster with a **Ship Timeline**,
and **Locate-a-ship** (search + per-ship show/hide) drives which ships render.
Engine gained `GET /fleet/{transponder}/route` (the timeline's segments); `/clock`
+ `/fleet/{tp}/state` (position + velocity vector) feed the live view. The engine
serves the built SPA same-origin at **`/ui`** (`HVSIM_UI_DIST`; multi-stage Docker
bundles it); the legacy Sol map stays at `/`. `just ui-dev` / `ui-build` /
`ui-check` (folded into `just check`). Sprint 024 added **junction queue panels**:
a nexus marker in the host system opens a live board (consuming 020's
`/junctions/{id}/queue`) — ordered real + phantom entries counting down
`transit in MM:SS` off the shared sim clock, `Esc` backing out progressively. That
closes the Phase-2c loop visually (resolver 019 → endpoint/metrics 020 → board 024).
Sprint 025 polished + **completed the Observer**: a dev-gated **time scrubber**
(play/pause via `rate 0`, rate presets, step, jump — `Space`/`,`/`.`), **faction
colours** (by transponder nation code), **layer toggles** (`l`), a **help overlay**
(`?`, rendering the keymap). Engine: `ClockUpdate.rate` now allows `0` (frozen).
**Phase 2.5 Observer is complete**; the **Controller** (file/route from the UI —
needs a `/plan` endpoint) is the next arc. Open polish lives in KWIs #69 (binary
geometry) / #70 (label clicks) / #71 (scale bar) / #72 (rich ship popup). Grafana
dashboards are a deferred parallel track. A UI/lore glossary lives in
`docs/terminology.md`.

**Galaxy data flow:** `data/` JSON (source of truth, CC BY-SA) → `just
derive-orbits` + `just frame` (fabricated orbits + Sol-origin galactic coords,
canon:false) → `just compile-data` → `build/universe.db` (artifact, contract
v0.3.0) → engine loads it (`HVSIM_UNIVERSE_DB`). The artifact carries systems
(coords, binary, per-star hyper limits), bodies, the wormhole route graph +
transit model, and the hyperspace bands. Query via `where-is --system <sys>
<body>`, `GET /systems`, `/wormholes`, `/junctions`, `/systems/{a}/distance/{b}`
(canon wormhole span if linked, else frame). **Sol is special-case:** it keeps
the real JPL ephemeris (artistic license — Sol tracks the *actual* current planet
positions), while Honorverse systems use fabricated orbits. No inter-system
*travel* until Phase 2b (the DES core).

**Growing the dataset:** use the `expand-galaxy` skill — it sequences the
`honorverse-*-scribe` skills (canon judgment) → the pipeline above → engine verify
→ a `docs/galaxy-changelog.md` entry. `just galaxy-summary` prints a markdown
snapshot of the artifact (built-vs-stubbed systems, counts of bodies/classes/ships/
links) so changelog entries are generated from truth, not memory.

- `planning/004-project-plan.md` is the authoritative design; read it first.
  (`001`–`003` are earlier M365 Copilot transcripts kept for context.)
- `sprints/` holds one short spec + task list per sprint. Check the highest-
  numbered file for what's in flight; a sprint is done only when every
  acceptance criterion in it is verified.

## What this project is

An "Honorverse" (David Weber) space-travel simulator. The **core value is
realism of the clock**: ships take real wall-clock hours/days/weeks to reach
their destinations, and the system reports where everything is *right now*.
It is deliberately **not** fast or flashy — do not optimize toward arcade-speed
travel or heavy graphics.

## Architecture intent (read before designing anything)

The system is decomposed so that the physics never mixes with world-building.
This separation is load-bearing — preserve it:

- **Ship simulator microservice (Phase 1, the current focus)** stays *dumb,
  deterministic, and math-driven*. It never invents lore, never computes routes.
  It compiles a filed flight plan into absolute-time `Segment` rows (each a
  closed-form piece of trajectory) and answers "where is everything at time T"
  analytically. **There is no game loop and no background physics tick** —
  state queries evaluate kinematics at the current timestamp. This gives zero
  drift and full cacheability; do not introduce a simulation loop.
- **`SimClock`** (epoch offset + rate multiplier) is the only time source.
  Production runs at rate 1.0 — that real-time pacing is the whole point.
  The rate/jump controls exist for dev and tests so a multi-hour trip can be
  fast-forwarded; never hardcode `now()` in domain code, go through the clock.
- **Universe builder, hyperspace/wormholes (Phase 2)** and **combat + LLM
  narrative + admiral agents (Phase 3)** are separate services added later.
  The ship simulator gains only new *segment kinds* (e.g. `hyper_cruise`,
  `wormhole_transit`); route planning and worldgen live outside it.

### Physics facts that constrain the math (verified in `004`)

- Newtonian kinematics with a velocity cap (0.6c). Reaching 0.6c at 250 g needs
  ~44 AU of runway, so the cap rarely engages in-system; relativity is a 2–6%
  effect and is only *reported* (`subjective_time_delta`), not simulated.
- In-system Sol trips are **brachistochrone** (accel, flip at midpoint, decel) —
  Earth→Saturn ≈ 12.7 h peaking at ~0.187c. The solver must handle both the
  brachistochrone case and accel/coast/decel, plus a moving-target intercept
  (the destination planet moves during the trip; solve by fixed-point iteration).
- Planet positions come from analytic JPL approximate Keplerian elements
  (J2000) — deterministic and offline, no external API calls.

Keep `ephemeris` and `kinematics` as **pure functions** so they are testable
without running the service.

## Monorepo layout (since Sprint 009 / Phase 2.0)

```
engine/      the hvsim engine — Python package + FastAPI service (MIT)
tools/       standalone tools, each its own pyproject (universe-compiler, etc.)
data/        Honorverse dataset, JSON source of truth — SEPARATE license (CC BY-SA)
contracts/   the language-agnostic seam: universe-artifact SQL DDL + engine OpenAPI
ui/          Phase 2.5 front-end — SvelteKit + Canvas-2D galaxy app (Sprint 021)
deploy/ grafana/ planning/ sprints/   ops, observability, design docs
justfile     workspace orchestration
```

The **engine is the only Python project at the moment**; it lives in `engine/`
(run `uv` from there). `data/` is **CC BY-SA 3.0** (its own `LICENSE`); the code
stays MIT. `contracts/` is versioned and frozen per minor version — it's what
keeps a future engine-only Rust port (and the tools/UI) decoupled.

## Toolchain & commands

Managed with `uv`. Python `>=3.12` (resolves to 3.13). **Engine commands run in
`engine/`:**

```sh
cd engine
uv sync                  # create .venv and install dev dependencies
uv run pytest            # run the engine test suite
uv run ruff check . && uv run ruff format --check .
uv run where-is saturn   # CLI: heliocentric position (--at <iso8601>, --list)
HVSIM_DEV_CLOCK=1 uv run uvicorn --factory hvsim.api.app:create_app --port 4667
```

From the repo root, the `justfile` orchestrates: `just check` (engine gate),
`just contracts` (validate the DDL + OpenAPI), `just build`/`deploy`/`health`/
`fleet`/`seed`. The validation gate before shipping is `just check` (pytest +
ruff + format), all clean.

Deployment via the root `justfile`: `just deploy` builds from `engine/` and ships
the image to the host; `just health`/`just fleet` query it. Target host/port come
from `.env` (`HVSIM_HOST`/`HVSIM_PORT`, default `kubsdb:4667`). Deployed instance
runs real time with `PUT /clock` off.

Deployment is driven by the root `justfile` (`just` to list recipes): `just
deploy` ships the image to the host and brings the stack up, `just health` /
`just fleet` query it, `just seed` files demo ships. The target host/port come
from `.env` (`HVSIM_HOST`/`HVSIM_PORT`, default `kubsdb:4667`); `cp .env.example
.env` to override. The deployed instance runs real time with `PUT /clock` off.

In comments/docstrings/strings, write math with the ASCII hyphen-minus `-`, not
the Unicode minus `−` (U+2212), which renders confusably. Ruff RUF001/002/003
enforce this; en/em dashes (`–`/`—`) are allowed for ranges and prose.

Package layout under `engine/src/hvsim/`: `ephemeris/`, `kinematics/`,
`flightplan/`, `route/`, `clock/`, `universe/`, `des/`, `api/`. Kinematics and
ephemeris stay **pure functions** — unit-testable without the service running.

**`des/` is the discrete-event execution core** (Sprint 013, Phase 2b
re-founding). Filed segments become boundary *events*; `Simulation.state(T)`
replays events up to `T` then evaluates the active segment analytically —
preserving the zero-drift, **no-loop** guarantee (events are sparse, one per
boundary; there is still no per-tick physics loop) while structurally admitting
the resolver-fixed, open-ended boundaries the Phase 2c wormhole queue needs.
`flightplan.state_at` delegates to it. The segment kinds are a closed set with
exhaustive dispatch (`des/model.py`) — the seam new travel modes plug into.
`SimClock` also carries the **PD calendar** (PD ↔ T-year ↔ epoch, anchored at
1890 PD); it labels the sim timeline without changing `now()`.

**`route/` is multi-mode interstellar travel** (Sprint 014). A filed `Route` of
mode-tagged legs (`nspace` / `hyper` / `wormhole`) compiles via `compile_route`
into DES segments: a hyper leg → an n-space **run out** past the origin star's
hyper limit + `hyper_cruise` (accel/coast/decel at apparent = band-multiplier × real velocity) + an n-space
**approach** to the target body; a wormhole leg → `wormhole_transit` (instant +
fixed `buffer_normal_s`). (The run-out/approach are the mundane impeller legs to
and from the hyper limit — *not* the Honorverse band "climb/descent".) Every
parameter (bands, per-star `hyper_limit_lmin`, distances, buffer) is **read from
the artifact** via new `Universe` accessors — the engine stays a configurable
physics box. In-system positions are heliocentric per system; an interstellar
`hyper_cruise` reports a **galactic-frame** position (`ShipState.frame` /
`.system` say which). The coast phase finally fires on long n-space legs. Demo:
`just demo-route` (Sol → Beowulf → Manticore → Grayson).

**Hyperspace band model** (Sprint 015) is **David Weber's own canon chart**
("Effective Speed By Hyper Band", recorded in `data/hyperspace/hyperspace.json`
with a special copyright note in [data/README.md](data/README.md)):
`apparent = velocity_multiplier(band) × real_cruise_velocity` (warship 0.6c /
merchant 0.5c). Each `ship_class` has a **`max_hyper_band`**; an individual ship
may **override** class stats (`ovr_*` columns → effective stat =
`COALESCE(ship.ovr_x, class.x)`, via `Universe.effective_ship`). Every ship must
have a class; a classless one gets an auto **`singleton`** class. The per-band
translation bleed-off + Iota-needs-streak-drive are recorded but not enforced on
v1 clocks (band-climb time is noise; only the 0.3c alpha-translation is a limit);
nation/era caps (e.g. Grayson pre-Alliance Gamma) await `ALLOW_ANACHRONISMS`
enforcement. Contract is **v0.2.0**.

**`tools/nav-planner/` is the route-finder** (Sprint 016) — the first tool that
depends on the engine package. Dijkstra over placed systems (hyper edges all-pairs
by frame distance with ship-aware band-speed weights; wormhole edges from the link
graph, weight ~buffer) → a **filed-route JSON** (`hvsim.route.to_filed` /
`from_filed`, the planner↔engine seam and the "flight plan for approval"). The
engine loads + flies it via `fly_filed_route`, guarded by
`Simulation.navigable_location(when)` — a phase-based derivation of the ship's
current navigable point (predeparture/layover/arrived → a body; in-motion → None):
outside dev mode the route origin must equal it, else reject (re-routing a moving
ship is deferred). `nav-plan` CLI / `just plan`. Route-finding stays in the tool;
physics stays in the engine.

**Transponder identity** (Sprint 017): every ship has a canonical dotted
**`nation.class.hull`** transponder (stable integer codes from
`data/transponder-codes.json` — nation codes are non-sequential: 0 unaffiliated,
1 Sol, 2 Beowulf reserved, others random-ish in [42,999]) plus an engine-only
**`modified`** bit (1 iff the hull carries an `ovr_*` override). The compiler
assigns + validates uniqueness; the engine resolves a transponder → effective
(class ⊕ override) stats (`Universe.transponder` / `ship_by_transponder` /
`effective_ship_by_transponder`, + `parse_transponder`/`format_transponder`).
Slug ids stay primary keys (transponder supplements). False-flag spoofing is
wartime (deferred). Contract is **v0.3.0**.

**Galaxy fleet API** (Sprint 018) — the deployed service operates galaxy routes,
**addressed by transponder**, alongside the Phase-1 Sol user-ship endpoints:
`POST /fleet/routes` (a planner filed-route JSON; persisted as the doc in a
`RouteRow` and **recompiled on query** — no segment-row churn), `GET
/fleet/{transponder}/state` (adds `system`/`frame`/vector), `GET /fleet` (the
board), `DELETE /fleet/{transponder}/route`. The at-origin guard runs at the
boundary (dev bypass). The artifact is **bundled into the image** (`just build`
stages `build/universe.db` → `engine/universe.db`; `HVSIM_UNIVERSE_DB` in compose).
`just shakedown [url]` plans + files a fleet and prints the board (a `?at=` sim-time
sweep). Planner stays client-side (no `/plan` endpoint).

SI units (m, s) internally; convert to km/AU and human-readable durations only
at the API boundary.
