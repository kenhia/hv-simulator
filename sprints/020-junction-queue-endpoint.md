# Sprint 020 — Junction queue endpoint (the deployed queue board)

Closes the Phase 2c loop on the **deployed** service and lays the data surface the
Phase 2.5 UI consumes. Sprint 019 built the queue resolver at the engine/CLI level,
but the deployed path resolves each route **in isolation** (phantom traffic only —
`resolve_route`). This sprint makes the service resolve the **whole active fleet
together** (real-ship interleaving) and exposes the queue two ways: per-ship on the
`/fleet` board, and junction-centric via the already-contracted `GET
/junctions/{id}/queue` (the "you are #3" view). Plus Grafana-ready metrics — the
first new data surface since we deferred dashboards, so we capture the time-series
now even though the panels come later.

First consumer: the UI **Sprint 024** (junction queue panels). Engine/API + ops
only this sprint.

## Goal

- `GET /junctions/manticore-junction/queue?at=<T>` returns the ordered transit
  queue at that junction at `T`: real ships (by transponder) **and** the phantom
  traffic ahead (anonymous), each with **position**, **mass**, and **transit ETA**.
- `GET /fleet` shows **interleaved** queue positions — two real ships filed through
  the same junction report distinct, correctly-ordered `queue_position`s (not two
  independent phantom-only queues).
- `/metrics` carries a **per-junction queue-depth** (and current-wait) gauge, ready
  to scrape into a Grafana time-series.

## Design

### Fleet-level resolution on the deployed path (the core change)
- A request-scoped helper gathers **all active `RouteRow`s**, compiles each, and
  runs `resolve_fleet([(compiled, transponder), ...])` (Sprint 019), returning a
  `transponder -> resolved CompiledRoute` map. `route_state` / `get_fleet` / the
  new queue endpoint all read from this map. **Supersedes** the per-route
  `resolve_route` on the deployed path — that was 019's documented deferral.
- Deterministic: same active fleet + `SIM_SEED` + `T` -> same queues, always.
- Cost is O(active routes) per query; fine at current scale (handful of ships).
  Memoize per request; optimize later if the fleet grows large.

### The junction queue snapshot
- For junction `J` at `T`: walk the resolved fleet for ships currently in a
  `wormhole_queue` segment at `J` (`t_start <= T < transit_open`), and the
  **phantom** transits ahead of them. Emit the merged, time-ordered occupants as
  `JunctionQueue.entries`: `{transponder | null, position, mass_tons,
  transit_eta}`, `position` counting `#1 = next to transit`.
- **Queue-server enhancement:** the 019 `JunctionServer` currently records phantom
  as anonymous `datetime` opens. To list phantom entries with mass + ETA (the
  contract's `ship_id: null` rows), the server must retain each phantom's
  `(mass, transit_open)`. Small extension to `TransitResolution` / `serve`.

### Contract reconciliation
- `contracts/engine-openapi.yaml` already declares `/junctions/{junction_id}/queue`
  + the `JunctionQueue` schema — **implement to it.** One reconciliation: the
  contracted entry key is `ship_id`, but the deployed API is **transponder**-
  addressed everywhere → change the schema field to `transponder` (`null` =
  phantom). (The broader OpenAPI↔`/fleet` drift is pre-existing debt, out of scope.)

### Metrics (Grafana forethought)
- Add per-junction gauges to `api/metrics.py`, labeled by `junction_id`:
  `hvsim_junction_queue_depth` (real ships queued now) and
  `hvsim_junction_queue_wait_seconds` (longest current wait). Rendered fresh each
  scrape, like the existing ship gauges (no module-global state). Dashboards are
  the deferred ops track; this just makes the series exist.

## Scope

1. **Fleet-level resolution helper** in the API; `/fleet` + state read from it
   (interleaved), replacing per-route resolution on the deployed path.
2. **`GET /junctions/{junction_id}/queue?at=`** -> `JunctionQueue` (real + phantom,
   ordered, position/mass/transit_eta). 404 unknown junction; 503 no universe.
3. **`/fleet` board** -> `FleetEntry` gains `queue_position` (+ transit ETA).
4. **Queue-server enhancement** — retain phantom `(mass, transit_open)` so the
   endpoint can enumerate phantom entries.
5. **Metrics** — per-junction queue-depth + current-wait gauges on `/metrics`.
6. **Tests** — API fleet interleaving (two ships -> ordered board positions);
   the queue endpoint (ordered entries incl. phantom; 404/503); metrics present
   + parseable; determinism.
7. **Demo** — `just queue-board` (or extend `just shakedown`) prints a junction's
   live queue from the running service.

## Out of scope

- **The UI** (Sprints 021+) — this is its data source.
- **Queue-knob auto-tuning**, multi-wormhole optimization, emergency/mass-transit
  buffers — later.
- **Broader OpenAPI ↔ `/fleet` drift cleanup** — only touch the queue endpoint +
  the fleet `queue_position` field.
- **Grafana dashboards** — deferred ops track; 020 only emits the series.
- **Combat** — Phase 3.

## Tasks

- [ ] Request-scoped fleet resolver (`resolve_fleet` over all active routes);
      `/fleet` + `route_state` use it; per-route resolve retired on the deployed path.
- [ ] `JunctionServer` retains phantom `(mass, transit_open)`; `TransitResolution`
      exposes ordered occupants for a snapshot.
- [ ] `GET /junctions/{junction_id}/queue` -> `JunctionQueue` (real + phantom,
      ordered; 404/503); schemas added.
- [ ] `FleetEntry.queue_position` (+ transit ETA); board reflects interleaving.
- [ ] Per-junction queue metrics in `api/metrics.py`.
- [ ] Tests (above); `just check` + `just contracts` green.
- [ ] `contracts/engine-openapi.yaml`: `JunctionQueue.ship_id` -> `transponder`;
      confirm the endpoint matches the implementation.
- [ ] `just queue-board` demo; CLAUDE.md + galaxy-changelog (if data/contract) +
      `planning/007` (mark 020 landed) updated; deploy + shakedown on kubsdb.

## Acceptance criteria

- `GET /junctions/{id}/queue?at=T` returns the contracted `JunctionQueue`: ordered
  `entries` (transponder, or `null` for phantom), `position` (`#1` = next),
  `mass_tons`, `transit_eta`; deterministic for fixed fleet+seed+T; 404 on unknown
  junction, 503 without the artifact.
- `GET /fleet` shows interleaved queue positions: two real ships filed through one
  junction report distinct, correctly-ordered `queue_position`s matching the engine
  resolver (A ahead of B).
- `/metrics` exposes per-junction queue depth + current wait (Prometheus parses),
  ready for a Grafana time-series.
- `just check` + `just contracts` green; OpenAPI updated; deployed to kubsdb and
  demoed live.

## Notes / decisions

- **Builds on 019's `resolve_fleet`.** The deployed path moves from per-ship
  phantom-only to fleet-level real interleaving — exactly the piece 019 deferred to
  020. The hard resolver already exists; this is wiring + a snapshot view + metrics.
- **Implements a pre-declared contract.** `engine-openapi.yaml` anticipated this
  endpoint; 020 makes it real, reconciling `ship_id` -> `transponder`.
- **Grafana checkpoint.** New data surface -> capture the time-series now (depth +
  wait); the dashboard work stays on the deferred ops track (`planning/007`).
- **Per-query fleet resolution** is acceptable at current scale; revisit if/when
  the active fleet reaches hundreds.
