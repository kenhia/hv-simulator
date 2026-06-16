# Sprint 018 — Galaxy API integration + deploy + live shakedown

Phase 2b.1, slice 2 (*operate the galaxy*). Wire multi-mode routes into the HTTP
service so a **planned route can be filed, flown, and watched** over HTTP — then
**deploy to `kubsdb`** and run the 5-ship shakedown live on an accelerated clock.
Ships are identified by their **transponder** (Sprint 017). The deployed engine-
level stack already passed its shakedown (50/50); this makes it operable as a
service.

## Goal

`POST` a planner-produced filed route for a ship (by transponder) → the service
flies it on the DES core → `GET` cross-system state + a **fleet board** that
advances on an accelerated dev clock. Deployed on `kubsdb`, 3–5 ships in flight
at once.

## Decisions baked in (prior sessions)

- **Ships are identified by transponder** (`nation.class.hull`) — the canonical
  identity from 017. A filed route references the ship by transponder; the service
  resolves it to effective (class ⊕ override) stats via the artifact.
- **Persist the filed-route doc + recompile on query** (not compiled segments):
  deterministic and cheap (the DES ethos), and it sidesteps serializing
  trajectories / galactic positions / the new segment kinds. A `RouteRow`
  (transponder, filed_json, status) is enough; `state(now)` rebuilds the
  `Simulation` from the doc.
- **Planner stays client-side** — no `/plan` endpoint (keeps the founding split;
  the service would otherwise depend on the planner tool). `nav-plan` emits the
  filed JSON; a seed/shakedown script `POST`s it.
- **At-origin guard at the boundary** via `Simulation.navigable_location` —
  outside dev mode, a ship must be at the route origin (at rest); re-routing an
  in-motion ship is rejected. **Dev mode** (`HVSIM_DEV_CLOCK`) bypasses.
- **Coexist with Phase 1** — the existing user-ship/Sol-flightplan endpoints stay
  untouched; galaxy routes are a new resource over artifact ships.
- **Reuse the existing clock controls** (`PUT /clock` rate/jump, gated by dev
  mode) for acceleration — no new clock machinery.

## Scope

### 1. Engine/route: transponder-addressed filed routes
- `route.to_filed`/`from_filed` reference the ship by **transponder** (resolve via
  `Universe.ship_by_transponder` → effective stats → route `Ship`). A small
  `ship_from_transponder` helper.

### 2. API: file + fly a route
- `POST /fleet/{transponder}/route` (or `/routes`) accepts a filed-route body
  (origin + legs). Resolves the ship by transponder; **at-origin guard** (dev
  bypass); `compile_route`; persist a **`RouteRow`** (transponder, filed_json,
  status=active, depart_at). 409 if already active (unless re-file/abort).
- `DELETE` / abort the active route.
- Persistence: store the **filed JSON**; recompile to a `Simulation` on query.

### 3. API: cross-system state + fleet board
- `GET /fleet/{transponder}/state?at=` → `StateOut` extended with **`system`**,
  **`frame`**, **transponder**, and the **vector** (velocity) — the "transponder +
  vector" squawk. Position formatted per frame (heliocentric km/AU; galactic ly for
  a `hyper_cruise` leg).
- `GET /fleet` → the board: each active route's transponder, ship, phase, system,
  ETA. (Generalizes `deploy/fleet.sh`.)

### 4. Ops: ship the artifact + deploy
- Bundle `build/universe.db` into the image (or mount it) and set
  `HVSIM_UNIVERSE_DB` in the deploy compose so the deployed service can resolve
  ships/routes. `just deploy` to `kubsdb`; `just health` includes the galaxy.

### 5. Live shakedown (the deliverable)
- A committed **`just shakedown`** (HTTP edition of `.scratch/shakedown.py`):
  plan 3–5 routes (`nav-plan`), `POST` them, set an accelerated clock
  (`PUT /clock`), and poll `GET /fleet` to watch the board advance. Run it against
  `kubsdb`.

## Out of scope

- **Wormhole queues** (the `tau(M)` wait) — Phase 2c.
- **False-flag / spoofing**, **unifying Phase-1 user ships with the catalog**,
  **re-routing an in-flight ship**, the **rich UI** — later.
- Multi-mode route filing for the *Sol user-ship* path (Phase-1 stays as-is).

## Tasks

- [x] `route`: transponder-addressed `to_filed`/`from_filed` + `ship_from_transponder`.
- [x] API: `POST /fleet/routes` (resolve transponder, at-origin guard w/ dev bypass,
      compile, persist `RouteRow` filed-doc), `DELETE` abort; recompile-on-query.
- [x] API: cross-system `GET /fleet/{transponder}/state` (system/frame/vector) +
      `GET /fleet` board; `StateOut`/schema extensions.
- [x] Ops: bundle the artifact into the image + `HVSIM_UNIVERSE_DB` in compose.
- [x] `just shakedown` (HTTP): plan → file 3–5 routes → board sweep. API tests
      (file/fly/state/fleet/guard/abort/needs-artifact).
- [x] `just check` + `just contracts` green; CLAUDE.md + plan updated. Contract
      unchanged (filed-doc lives in the service DB, not the artifact).
- [ ] **Deploy to `kubsdb`** and run the live shakedown (after the local HTTP
      checkpoint — which passed).

## Acceptance criteria

- A planner route filed over HTTP for a ship (by transponder) **flies on the
  service**: `GET /fleet/{transponder}/state` reports phase/system/frame/vector
  across the trip; `GET /fleet` lists the active fleet with ETAs.
- The **at-origin guard** rejects filing for a ship not at the route origin
  (outside dev mode); dev mode bypasses; an in-flight ship can't be re-routed.
- **Deployed on `kubsdb`** with the artifact bundled; `just shakedown` plans +
  files 3–5 ships and the fleet board **advances on an accelerated clock** to
  arrivals.
- Phase-1 Sol endpoints still work; `just check` + `just contracts` green.

## Notes / decisions

- **Why recompile-on-query:** routes are deterministic functions of (filed doc,
  artifact, T). Storing the doc + recompiling avoids persisting `Trajectory` /
  galactic-frame / `hyper_cruise` rows and keeps a single source of truth. Perf is
  a non-issue (sparse events).
- **Size:** this is a large sprint (API + persistence + ops + deploy + shakedown).
  If it runs long, split at the deploy line: "API-ready + local HTTP shakedown"
  now, "kubsdb deploy + live run" as a fast follow.
- **Identity end-to-end:** transponder is now the through-line — planner → filed
  JSON → API → fleet board → (future) UI/combat. The slug ids stay for authoring.

## Outcome

API built + **local HTTP shakedown passed**. New galaxy fleet endpoints
(transponder-addressed, coexisting with the Phase-1 Sol path):
`POST /fleet/routes` (planner filed-route JSON → at-origin guard → compile →
persist a `RouteRow` storing the filed doc), `GET /fleet/{transponder}/state`
(StateOut + `system`/`frame`/`transponder` + vector), `GET /fleet` (board),
`DELETE /fleet/{transponder}/route`. State **recompiles from the filed doc** each
query (deterministic; no segment-row churn). Route layer adopted transponders
(`to_filed`/`from_filed`/`ship_from_transponder`); the planner CLI emits the
transponder.

Ops: the artifact is **bundled into the image** (`just build` compiles + stages
`build/universe.db` → `engine/universe.db` → `COPY` in the Dockerfile;
`HVSIM_UNIVERSE_DB` set in the deploy compose). `just shakedown [url]` plans +
files a 5-ship fleet and prints a `?at=` board sweep (clock-rate set is best-effort
— skipped in production).

Local checkpoint (`uvicorn` + the artifact): all 5 routes filed; the board
advanced correctly — T+2d the wormhole hops (Reliant/Athena) arrived while the
hyper ships cruised interstellar, T+15d Nike arrived + Starhauler 95.6% into its
Manticore approach, T+40d all arrived. `just check` (109 engine + all tools +
`data OK`) + `just contracts` green; contract unchanged (v0.3.0).

**Pending: deploy to `kubsdb` + live run** (the local checkpoint was clean, so per
plan we proceed to deploy).
