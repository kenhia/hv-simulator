# Sprint 016 — Nav route planner (tools/nav-planner)

Closes **Phase 2b**. Adds the **route-finder**: given a ship and a destination,
search the system graph and emit a **filed multi-mode route** (n-space / hyper /
wormhole legs) the engine flies. Per the founding split the planner is **not**
physics and lives in `tools/` — it picks the *topology* (which systems, which
modes); the engine remains the source of truth for the executed clock. Built
**UI-first in intent**: the output is a presentable "flight plan for approval".

## Goal

`nav-plan --ship <id> --from <system>:<body> --to <system>:<body>` → a filed-route
JSON (ordered mode-tagged legs) + an ETA estimate; the engine **loads and flies**
it, and a demo proves **plan → execute → clock** end-to-end (e.g. auto-plan
Sol → Grayson for a ship and fly it).

## Decisions baked in (this session)

- **Planner depends on the engine package** (path dep): reuses `Universe` /
  `effective_ship` to read the artifact and the `Route` / `RouteLeg` /
  `compile_route` / `ship_from_artifact` types. First tool to depend on the
  engine — justified because it produces engine-consumable routes and reasons
  about ship band stats. Route-*finding* logic stays in the tool, not the engine.
- **Output is a filed-route JSON** — the presentable, persistable plan a UI shows
  for approval. The engine gains `Route` ↔ filed-dict (`to_filed` / `from_filed`)
  so the JSON round-trips to execution. (Promote the format to `contracts/` later
  if a non-Python UI/planner needs it; documented in the tool for now.)
- **Plan AND fly end-to-end** this sprint (engine loads the planned route; a demo
  flies it and shows the clock).
- **Ship-at-origin precondition — derived from current state, no new field.**
  The engine can already tell where a ship is from its active plan's `ShipState`:
  add `Simulation.navigable_location(when) -> (system, body) | None`, keyed on
  **phase** (not raw speed):
  - `predeparture` → origin `(system, body)`; `layover` → the layover body
    (the active segment carries `body` + `system`); `arrived` → final body — all
    **navigable**.
  - `transit` / `hyper_cruise` / **`wormhole_transit`** → **None** (in motion; note
    wormhole_transit reports speed 0 but is *not* navigable — hence phase-based).
  Outside **dev mode**, flying a planned route **rejects** unless its origin equals
  the ship's `navigable_location(now)` — semantically "abort the current plan,
  accept the new one" from a navigable point. Dev mode bypasses (test/fast-forward).
  **Re-routing a ship that already has a vector is deferred** (None → rejected);
  a persistent "ship location" field for *idle* ships (no active plan) may follow.
- **Cost = travel time; v1 returns the single fastest route.** The planner
  estimates leg times for the graph search (reads band speed + hyper limit + buffer
  from the artifact); the engine gives the authoritative clock on execution.
  Alternatives / multi-criteria (fewest wormholes, fuel) are deferred.

## The graph + search

- **Nodes:** placed systems (those with galactic coordinates).
- **Hyper edges:** every pair of placed systems; weight = the ship's estimated
  hyper time = `frame_distance / (multiplier(ship max_band) × real_cruise_velocity)`
  plus a small fixed n-space run-out/approach allowance. (Distance is the
  galactic-frame straight line — what a hyper leg actually flies.)
- **Wormhole edges:** each canon wormhole link (skip null/unidentified termini);
  weight ≈ `transit_model.buffer_normal_s` (near-instant) — so a junction hop
  beats a long hyper leg whenever one exists.
- **Search:** Dijkstra (min total time) origin-system → destination-system →
  an ordered list of `(mode, to_system)` hops.
- **Leg translation:** hops become `RouteLeg`s; intermediate legs arrive at the
  limit/nexus (`to_body=None`), and the route ends with the **destination body**
  (a hyper leg's approach targets it; a final wormhole hop gets a trailing
  `nspace` leg to the body). Origin = `(from_system, from_body)`.

## Scope

### 1. `tools/nav-planner/` (own pyproject; path dep on the engine)
- Graph build + Dijkstra over the artifact; ship-aware time weights.
- Emits a **filed-route JSON**: `{ship, origin:{system,body}, legs:[{mode,to_system,to_body?}], estimate:{eta_s, generated_*}}`.
- `nav-plan` CLI (`--ship/--from/--to/--db/--out`): human-readable summary +
  JSON. Errors clearly on unreachable / unplaced / unknown ship.

### 2. Engine: filed-route round-trip + navigable-location guard
- `hvsim.route`: `to_filed(route)` / `from_filed(dict, u)` (build a `Route` from a
  filed doc, resolving the ship via `ship_from_artifact`).
- `Simulation.navigable_location(when) -> (system, body) | None` (phase-based, per
  the decision above) — derives the ship's current navigable point from its active
  plan/route; no new persistent field.
- A **fly-a-planned-route** entry point that, **unless dev mode**, requires the
  route origin to equal the ship's `navigable_location(now)` (else reject:
  in-motion, or at a different body). "Accept new" = abort the current plan.

### 3. Demo + tests
- `just plan` — plan a default route (e.g. a ship → Grayson) and **fly it**,
  printing the legs + clock (plan→execute end-to-end).
- Tests (in the tool + engine): Dijkstra picks the **wormhole shortcut** when it's
  faster and **pure hyper** when no link helps; a higher-band ship's plan is
  faster; the filed JSON round-trips to a `Route` and the engine flies it (clock
  matches `compile_route`); destination body is reached. **`navigable_location`**
  returns the right `(system, body)` for predeparture/layover/arrived and **None**
  for transit/hyper_cruise/**wormhole_transit**; the guard rejects an in-motion or
  wrong-body origin and dev mode bypasses.

## Out of scope

- **Alternatives / multi-criteria** (fewest transits, fuel, risk) — later.
- **Re-routing an in-flight ship** (a ship with an existing vector) — deferred.
- **HTTP / persistent filing** of planned routes, and the **actual UI** — later
  (the JSON is the seam they'll build on).
- **Wormhole queue costs** (the `tau(M)` wait) — Phase 2c; v1 uses the fixed buffer.
- **Corona-flyby / obstacle doglegs** — known simplification (plan notes).

## Tasks

- [x] `tools/nav-planner/` scaffold (pyproject, path dep on engine) + artifact
      graph build (placed systems; hyper all-pairs; wormhole edges).
- [x] Dijkstra (ship-aware time weights) → hop list → `RouteLeg`s → filed-route
      JSON; `nav-plan` CLI with clear errors.
- [x] Engine: `Route` `to_filed`/`from_filed`; `Simulation.navigable_location`;
      `fly_filed_route` entry point with the navigable-location guard (dev bypass).
- [x] `just plan` end-to-end demo (plan → fly → clock); tests per the list above.
- [x] `just check` (engine + all tools incl. nav-planner) + `just contracts` green;
      CLAUDE.md + plan updated. Contract unchanged (v0.2.0).

## Acceptance criteria

- `nav-plan` produces a filed-route JSON for a ship+destination; the engine
  **loads and flies** it with a realistic clock — proven end-to-end by `just plan`.
- The planner picks the **time-optimal** system path: a wormhole hop when it beats
  hyper, straight hyper otherwise; a faster ship yields a faster plan.
- Flying a planned route **respects the at-origin precondition** (rejected outside
  dev mode when the ship isn't at the origin); dev mode bypasses.
- Planner is a standalone `tools/` package (own pyproject) that stays out of the
  engine's physics; the engine only gains route (de)serialization + the guard.
- `just check` + `just contracts` green.

## Notes / decisions

- **Estimate vs truth:** the planner's leg-time weights are *estimates* for
  choosing a path; the engine's `compile_route` is the clock of record. Small
  divergence is fine — the planner picks topology, the engine flies physics.
- **Navigable location is derived, not stored:** the active plan's `ShipState`
  already pins a ship to a body when at rest (predeparture/layover/arrived), so the
  guard needs no new field. A persistent location is only needed for *idle* ships
  (no active plan) — a likely next-sprint add. Re-routing a moving ship (carry its
  vector into a new plan) stays the deferred follow-on.
- **Why depend on the engine:** avoids duplicating the artifact-read + band model;
  the route format is shared in one place. A future Rust/non-Python planner would
  instead read the artifact + the filed-route JSON contract directly.

## Outcome

Done — **Phase 2b closed**. New `tools/nav-planner/` (own pyproject, path-dep on
the engine): Dijkstra over placed systems with **hyper** edges (all-pairs, ship
band-speed weights) + **wormhole** edges (only `transit == "instant"` links — the
table also holds `hyper_leg`/`transfer` annotations that are *not* hops). Assembles
the hop list into `RouteLeg`s ending at the destination body, and emits a
**filed-route JSON**. `nav-plan` CLI + `just plan`.

Engine additions: `hvsim.route.to_filed`/`from_filed` (the filed-route seam,
schema `hvsim.filed-route/v1`); `fly_filed_route` with the at-origin guard;
`Simulation.navigable_location(when)` (phase-based: predeparture/layover/arrived
→ `(system, body)`; transit/hyper_cruise/wormhole_transit → None). The guard
rejects flying a route whose origin ≠ the ship's current navigable point unless
dev mode; re-routing an in-motion ship is deferred.

**`just plan` proves it end-to-end:** auto-plans HMS Nike Sol → Grayson →
`hyper sigma-draconis → wormhole manticore → hyper grayson`, ETA **11.14 d** —
the same optimal route the 014/015 deliverable hand-filed. A found bug
(`hl-sol-sigma-draconis` is a `hyper_leg`, not a wormhole) is fixed by the
`transit == "instant"` filter. Tests: nav-planner (6 — wormhole-vs-hyper choice,
non-instant link ignored, faster ship, round-trip+fly, unreachable) + engine
(navigable_location by phase incl. layover, filed round-trip, guard accept/reject/
dev-bypass). `just check` (98 engine + all four tools) + `just contracts` green;
contract unchanged (v0.2.0).
