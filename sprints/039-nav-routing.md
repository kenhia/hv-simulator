# Sprint 039 — Nav & routing

korg proposal **185**. Three route/queue-mechanics items, all engine-side (plus a
thin UI surface for the headline feature):

- **#59 — Repeating itineraries** (L). Ships that *live on a loop*: file a
  round-trip once and the simulator flies it forever, no manual re-filing. The
  standing design is [035-repeating-routes.md](035-repeating-routes.md) — this
  sprint executes it rather than re-deriving it.
- **#67 — In-flight ships shouldn't lose queue position to later filings** (M).
  A junction slot is recomputed from the live fleet on every query and ordered by
  junction-arrival, so a ship filed *after* you departed can be slotted ahead of
  you and push your ETA later.
- **#64 — Precompute the nav route graph** (M). The route-finder rebuilds the
  whole all-pairs hyper graph on every search. Precompute the static topology
  once per artifact and cache the per-speed routing tables; keep costing the
  dynamic last mile per request.

## #67 — Queue fairness (do this first)

The invariant to establish: **a route filed at time *f* never perturbs the
resolved timeline of a route filed before *f*.** That is stronger than "in-flight
ships keep their slot" and much easier to reason about — and it makes the queue
board stable as the fleet grows.

Two changes:

1. `JunctionServer` becomes a **reservation calendar** instead of a monotone
   `busy_until` cursor. `serve()` first-fits the ship's block (its phantom, then
   itself, back-to-back) into the earliest gap at or after arrival that doesn't
   overlap an existing reservation. Order of insertion no longer has to be
   arrival-ordered, and a later arrival can still use an idle nexus.
2. `resolve_fleet_junctions` folds routes in **filing order** (`filed_at`, then
   ship key) rather than global arrival order. Since a reservation never moves an
   existing one, every earlier-filed route resolves identically no matter what is
   filed later.

Queue *positions* are then recomputed in a final pass from the finished server
(opens strictly before the ship's own transit-open), so the reported `#N` agrees
with the junction board even when a later filing slotted into a gap.

The API passes `RouteRow.created_at` as `filed_at`.

## #59 — Repeating routes

Per the 035 design; the load-bearing constraint is unchanged: **no background
tick**. A repeating route is a template + a start time that analytically defines
an infinite sequence of cycles; a query at T walks to the covering cycle and
compiles just that one.

- `hvsim.route.repeat`: `LayoverSpec`, `CycleRule`, `RepeatingRoute`,
  `layover_for` (deterministic `hash(seed, cycle, stop)` draw within the range,
  overridable by an `every-N` rule), `cycle_route`, `route_at`.
- Cycle walk is memoized per filed document (the boundaries are deterministic, so
  the cache is pure memoization — each cycle compiles once, ever).
- Filed schema **`hvsim.repeating-route/v1`**; `RouteRow` is unchanged (the doc is
  stored verbatim and recompiled on query).
- API: `POST /fleet/routes` accepts either schema; every read path resolves the
  *active cycle* for the queried instant; `StateOut`/`RouteOut`/`FleetEntry` gain
  `cycle` + `cycles`.
- UI: a **repeat** toggle in the Flight Planner (loop back to origin, layover
  range, forever/N) and a **↻ cycle N** indicator on the board + ship detail.
- `just seed-routes` files a couple of repeating couriers so the map bustles.

## #64 — Route-graph precompute

- `hvsim.route.graph`: a `RouteGraph` (placed systems, coordinates, all-pairs
  distances, wormhole adjacency, buffer) built **once per artifact** and cached on
  the `Universe`.
- Hyper-edge weight is `dist_ly * k + overhead` with `k = T_year / (band_mult *
  cruise_c)` — one scalar per ship *speed class*, so the Dijkstra predecessor
  table caches per `(k, origin)` and every later search for a same-speed ship is a
  table walk.
- `_search` becomes a lookup; the finder still costs the dynamic last mile
  (in-system legs, real clocks) per request via `compile_route`.
- Warmed at app startup when an artifact is loaded.

## Tasks

- [ ] #67: reservation-calendar `JunctionServer` + filing-order fold + position
      repair pass; tests (a later filing cannot move an earlier one; a later
      arrival still uses an idle nexus; determinism preserved).
- [ ] #67: API passes `filed_at` from `RouteRow.created_at`.
- [ ] #64: `RouteGraph` + cached routing tables; identical routes to the naive
      search; cache hit proven by test.
- [ ] #59: engine `repeat` module + schema round-trip + `route_at`; tests.
- [ ] #59: API accepts the repeating schema, resolves the active cycle on every
      read path, reports `cycle`/`cycles`; tests.
- [ ] #59: UI repeat toggle + ↻ cycle indicator; `api.ts` types.
- [ ] #59: `just seed-routes`.
- [ ] `just check` + `just contracts` + `just ui-check` green; CLAUDE.md note.

## Acceptance criteria

- Filing a new route never changes an already-filed route's junction slot or ETA
  (the #67 invariant), and the queue board's `#N` agrees with the resolved times.
- A ship filed on a repeating route cycles indefinitely with no background loop;
  state at any T is analytic and re-querying T is identical.
- Layovers vary within their range but are deterministic across restarts.
- The board shows `↻ cycle N`; an N-cycle route ends `arrived` at origin.
- Route-finding returns the same topology as before, from a cached graph.
