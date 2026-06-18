# Sprint 026 — engine: the `/plan` endpoint (Controller opener)

The first Controller sprint and an **engine** one: relocate the route-finder into
`hvsim` and expose **`POST /plan`** so the UI can plan multi-destination routes over
HTTP and preview them before filing. No UI yet (that's 027) — this lays the
endpoint the Flight Planner consumes.

Plan + decisions: [`planning/007`](../planning/007-ui-vision.md) (Controller
section, resolved 2026-06-18).

## Goal

`POST /plan` takes a ship + origin + an **ordered list of waypoints** (with optional
layovers) and returns the **filed-route JSON** (`to_filed` shape) *plus* a compiled
**preview** (segments + ETA), computed but **not filed**. The UI previews it, then
commits via the existing `POST /fleet/routes`.

## Design

### 1. Relocate the route-finder into `hvsim` (the architectural change)
- Move the Dijkstra finder from `tools/nav-planner/nav_planner` into **`hvsim.route`**
  (a new `hvsim/route/find.py`): `_distance_ly`, `_hyper_time_s`, `_placed_systems`,
  `_wormhole_adjacency`, `_search`, `_legs`, `plan_route`. Pure graph over `Universe`;
  no new deps. Export `plan_route` (and a new multi-waypoint planner, below) from
  `hvsim.route`.
- `tools/nav-planner` becomes a **thin CLI wrapper**: `nav_planner` re-exports
  `plan_route` from `hvsim.route` and keeps `main` (`nav-plan` / `just plan`). Its
  test imports `from nav_planner import plan_route` and stays green via the re-export.
- **Revises** the prior "route-finding stays in the tool" principle (007): HTTP
  planning makes finding a first-class engine capability. Physics + finding both in
  `hvsim`; the UI still owns no logic.

### 2. Multi-destination planner
- Add `plan_route_multi(u, ship_id, origin_system, origin_body, waypoints, depart_at)`
  where `waypoints = [(system, body, layover)]`. For each consecutive `(from, to)`
  hop it runs `_search` + `_legs`, sets the reaching leg's `layover`, and
  concatenates into **one** `Route`. Single-destination is a one-waypoint list.
  (The engine `Route`/`compile_route` already fly multi-leg — only the *finder*
  needed the waypoint loop.)

### 3. `POST /plan`
- Body: `{ ship (transponder), origin: {system, body}, waypoints: [{system, body,
  layover_s?}] }`.
- Resolve ship by transponder → `ship_id`; `plan_route_multi(...)`; `compile_route`
  for the preview; `to_filed` for the doc.
- Returns `{ filed: <filed-route doc>, route: <RouteOut> }` — `filed` is what the UI
  POSTs to `/fleet/routes`; `route` is the preview (segments, ETA, arrival, total).
- Errors: 404 unknown ship / system / body; 422 unroutable (`ValueError` from the
  finder); 503 without the artifact. **Does not file** anything; **does not** add a
  min-layover (UI-enforced — 007/027).
- Departure: default the sim clock's `now()` (consistent with `POST /fleet/routes`),
  or accept an optional `depart_at`.

### 4. Schemas + contract
- `PlanRequest` (ship, origin, waypoints), `PlanOut` (`filed` + `route: RouteOut`).
  Add `/plan` to `contracts/engine-openapi.yaml`.

## Scope

1. `hvsim/route/find.py` — relocated finder + `plan_route` + `plan_route_multi`;
   exported from `hvsim.route`.
2. `tools/nav-planner` — thin wrapper re-exporting `plan_route`; CLI intact.
3. `POST /plan` (multi-waypoint) → `{filed, route}`; 404/422/503; no filing, no
   auto-layover.
4. Schemas (`PlanRequest`/`PlanOut`) + OpenAPI `/plan`.
5. Tests: relocated-finder unit tests (move/keep) + nav-planner CLI test green;
   engine `/plan` tests (single + multi-waypoint, layover passthrough, 404/422).
6. `just check` + `just contracts` green; `just plan` still works; deploy.

## Out of scope

- **The Flight Planner UI** — 027 (this is its data source).
- **Saved routes, arbitrary/non-traditional waypoints, re-routing a moving ship** —
  028.
- **Min-layover enforcement in the engine** — UI-enforced for now (007); revisit
  when it needs to vary.
- **A `/plan`-then-file one-shot** — keep plan (preview) and file (commit) separate,
  so the UI always previews first.

## Tasks

- [ ] Relocate the finder into `hvsim/route/find.py`; export `plan_route` +
      `plan_route_multi`; `nav_planner` re-exports; CLI + its test green.
- [ ] `POST /plan` (multi-waypoint) → `{filed, route}`; errors; no filing/no layover.
- [ ] `PlanRequest` / `PlanOut` schemas; OpenAPI `/plan`.
- [ ] Engine tests (single + multi + layover + 404/422); `just plan` smoke.
- [ ] `just check` + `just contracts` green; deploy.

## Acceptance criteria

- `POST /plan` with one waypoint returns a filed-route doc + a compiled preview
  (segments + ETA) without filing; submitting that `filed` to `POST /fleet/routes`
  succeeds.
- `POST /plan` with **multiple ordered waypoints** returns a single concatenated
  route visiting them in order, honouring per-waypoint layovers.
- Unknown ship/system → 404; unroutable → 422; no artifact → 503.
- `nav-plan` / `just plan` still work (finder relocated, CLI a thin wrapper);
  `just check` + `just contracts` green.

## Notes / decisions

- **Engine-only sprint** — sets up 027's Flight Planner. The split (plan = preview,
  file = commit) keeps the UI honest: always preview before committing.
- **Finder relocation** is the load-bearing change; keep it a clean move (same
  logic, new home) so the diff is reviewable and the CLI/tests are unaffected.
- Multi-destination is **core** here, not a later add — the planner just loops the
  finder over consecutive waypoints; the rest of the stack already flies multi-leg.
