# Sprint 035 — Repeating routes (ships that live on a loop)

> **⏸ DEFERRED (not the next sprint).** This spec was drafted, then set aside when
> the "dashboard pass" (korg proposal **177**) was started ahead of it. Repeating
> routes is korg proposal **185 — nav & routing**; when that proposal is actually
> started, its sprint doc should **refer back to this design** rather than
> re-deriving it. Kept here (with its 035 number) as the standing plan. Numbering
> stays sequential — the dashboard-pass sprint takes the next number.

Make the galaxy feel **alive**: a ship can be filed on a **repeating itinerary** it
cycles forever (couriers shuttling, transports looping) — without manual re-filing
and **without a game loop**. The per-trip mechanics stay the existing compiled
segments; the route just analytically defines an infinite sequence of cycles and we
evaluate the active one at query time. KWI #59.

Plan: `planning/004` (no-loop principle), `planning/007` (slice 035). Engine + a
thin UI surface. **L** sprint.

## The load-bearing principle (read first)

**No background tick.** Like `state_at`, a repeating route is *lazy + analytic*: a
template + a start time deterministically define every cycle; a state query at time
T computes **which cycle/leg is active** and compiles just that cycle. Storage stays
tiny (the template, not per-trip rows). This preserves zero-drift and cacheability —
do not introduce a per-tick simulation.

## Model (engine)

A **repeating route** = a round-trip the ship repeats. Reuse the existing pieces:

- A cycle is a normal multi-leg `Route` (origin → waypoints → **back to origin**)
  compiled by `compile_route` — deterministic given its depart time. Cycle *N+1*
  departs when cycle *N* ends (after its final layover).
- The **topology is stable** across cycles (same systems/modes); only the depart
  time and in-system durations differ (planets move). So store the round-trip
  **legs once**; recompile per cycle with that cycle's depart time.
- **Layovers are deterministic, not stored per trip:** each stop carries a layover
  **range** `[min, max]` (or a fixed value); the value for a given cycle =
  `min + frac(hash(seed, cycle_index, stop_index)) * (max - min)`. Reproducible,
  tiny storage (template + seed + start).
- **End condition:** `cycles: null` (forever — the "alive" default) or an integer N
  (after N cycles the ship arrives at origin and stays `arrived`). `DELETE` stops it.
- Optional **cycle rule(s)** (the motivating "every 5th trip, Earth layover 12 h"):
  a small list `[{every: N, stop: i, layover_s: X}]` overriding a stop's layover on
  matching cycles. *(v1: support one simple rule list; defer richer rules.)*

New in `hvsim.route`:
- `RepeatingRoute` dataclass (ship, origin, round-trip legs, per-stop layover specs,
  seed, start_at, cycles, rules).
- `route_at(rep, when, u) -> (cycle_index, CompiledRoute)` — lazily walk cycles from
  `start_at`, accumulating each cycle's compiled duration until the one covering
  `when`; compile + return it. Cache accumulated cycle boundaries (the deployed
  clock advances monotonically, so the walk is short and amortized).
- `to_filed` / `from_filed` for a new schema **`hvsim.repeating-route/v1`**.

## API

`RouteRow.filed_json` already stores the doc verbatim and recompiles on query — so a
repeating route is **the same row with a different schema**; no DB change.

- `POST /fleet/routes` accepts a `repeating-route/v1` doc (round-trip legs +
  `repeat: {layovers, cycles, seed, rules}` + `start_at`). The at-origin guard
  applies to the first cycle.
- Query paths (`route_compiled` / `resolved_fleet` / `GET /fleet/{tp}/state` /
  `route`) detect the schema: repeating → `route_at(rep, now, u)` gives the active
  cycle's `CompiledRoute`, then existing `state_out` / segment serialization apply.
- **State** gains a `cycle` (and `cycles` total / null) field; phase still cycles
  transit→layover→… (a forever route is never `arrived`). The wormhole-queue
  resolver interleaves repeating ships via their active cycle (so they queue like
  anyone else).
- `DELETE /fleet/{tp}/route` stops it (unchanged).

## UI (thin)

- **Flight Planner:** a **"repeat"** toggle. When on, the route loops back to the
  origin and is filed as a repeating route; expose a simple **layover range** (min/max
  hours, with a sensible default) and **forever / N cycles**. (Reuses the existing
  multi-destination planner + `POST /plan` preview for one cycle.)
- **Fleet Board / ship detail:** a repeating ship shows a **↻ cycle N** indicator
  next to its phase; detail lists the loop + current cycle.

## Demo / seed

- A `just seed-routes` (or extend `just shakedown`) that files a couple of repeating
  couriers (e.g. an Earth↔Mars run, a Manticore↔Trevor's hop) so the map bustles
  unattended — the "alive" payoff.

## Tasks

- [ ] Engine: `RepeatingRoute` + `route_at` (lazy cycle walk, deterministic layovers,
      end condition, optional rule list) + `to_filed`/`from_filed`; unit tests
      (cycle boundaries deterministic; layovers in range + reproducible; cycle N
      depart = cycle N-1 end; forever vs N-cycle termination).
- [ ] API: accept the repeating schema on `POST /fleet/routes`; schema-detect in the
      query paths; `cycle`/`cycles` on `StateOut`; resolver interleaving; tests.
- [ ] UI: planner repeat toggle (loop + layover range + forever/N) → files repeating;
      board/detail `↻ cycle N` indicator; `api.ts` types.
- [ ] `just seed-routes` demo recipe.
- [ ] `just check` + `contracts` green (schema additive); changelog/CLAUDE.md note.

## Acceptance criteria

- A ship filed on a repeating route cycles indefinitely with **no background loop**:
  state at any T is computed analytically; re-querying the same T is identical.
- The fleet board shows it cycling (↻ cycle N), never stuck "arrived" (forever case);
  an N-cycle route ends `arrived` at origin after N.
- Layovers vary within their range but are **deterministic** (reproducible across
  queries/restarts).
- Repeating ships interleave correctly at wormhole junctions.
- `just seed-routes` populates a visibly busy galaxy; all gates green.

## Out of scope (deferred)

- Rich cycle-rule DSL (v1 = one simple `every-N` override list).
- Mid-cycle re-routing / dynamic destination changes.
- Per-ship economic/cargo modelling (this is movement only).
- Non-traditional waypoints (belt/mid-space) — Controller-extras territory.
