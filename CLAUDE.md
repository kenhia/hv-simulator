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
the `expand-galaxy` orchestrator skill. Design is in `planning/006`; the engine is
being re-founded on a lazy discrete-event core (DES) for travel/queues in 2b/2c.

**Galaxy data flow:** `data/` JSON (source of truth, CC BY-SA) → `just
derive-orbits` + `just frame` (fabricated orbits + Sol-origin galactic coords,
canon:false) → `just compile-data` → `build/universe.db` (artifact, contract
v0.1.1) → engine loads it (`HVSIM_UNIVERSE_DB`). The artifact carries systems
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
ui/          Phase 2.5 front-end (placeholder)
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
into DES segments: a hyper leg → n-space **climb** past the origin star's hyper
limit + `hyper_cruise` (distance ÷ band apparent velocity) + **descent**; a
wormhole leg → `wormhole_transit` (instant + fixed `buffer_normal_s`). Every
parameter (bands, per-star `hyper_limit_lmin`, distances, buffer) is **read from
the artifact** via new `Universe` accessors — the engine stays a configurable
physics box. In-system positions are heliocentric per system; an interstellar
`hyper_cruise` reports a **galactic-frame** position (`ShipState.frame` /
`.system` say which). The coast phase finally fires on long n-space legs.
**Route-finding is Sprint 015's `tools/nav-planner/`** — routes here are
hand-filed. Demo: `just demo-route` (Sol → Beowulf → Manticore → Grayson).

SI units (m, s) internally; convert to km/AU and human-readable durations only
at the API boundary.
