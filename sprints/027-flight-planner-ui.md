# Sprint 027 — the Flight Planner UI (Controller)

File and route ships **from the UI**: pick a ship, choose an origin + ordered
destinations (with layovers), preview the computed route on the map, and submit it
to the live fleet. The first **Controller** surface — Observer + write actions,
consuming 026's `POST /plan` and the existing `POST /fleet/routes` /
`DELETE /fleet/{tp}/route`.

Plan: [`sprints/planning/007`](planning/007-ui-vision.md) (Controller section).

## Goal

Open the Flight Planner (menu `m`) → pick an available ship → set origin + a
sequence of destinations + layovers → **Plan** (`POST /plan`) → see the route
previewed on the map (legs + ETA + Ship Timeline) → **Submit** (`POST
/fleet/routes`) and watch it join the live board. Abort an active route from the UI.

## The data

- **New: `GET /fleet/ships`** — a galaxy **ship catalog** the picker needs (none
  exists; `/ships` is the Phase-1 Sol CRUD). Per ship: `{ transponder, name,
  nation_code, class, military, has_active_route }`. `military` from
  `ship_classes.navy` (a navy ⇒ military), driving the UI min-layover rule;
  `has_active_route` so the UI can flag in-flight ships (re-routing is 028). New
  `Universe.ships()` accessor.
- `POST /plan` (026) → `{filed, route}` preview. `POST /fleet/routes` commits the
  `filed` doc. `DELETE /fleet/{tp}/route` aborts. `/systems` + `/systems/{id}/bodies`
  (+ `/places`) populate the origin/destination pickers.

## Design

### Controller surface (menu `m`)
- The reserved `m` opens the **Flight Planner** panel (the Controller surface);
  Observer remains the default. v1 = a panel, not a full mode-swap shell.

### The planner
- **Ship** — pick from `GET /fleet/ships`. Show nation colour + `military`;
  in-flight ships (`has_active_route`) are flagged (submitting will hit the
  at-origin guard → 028).
- **Origin** — system + body pickers (`/systems` → `/systems/{id}/bodies`/`places`).
  An **idle** ship files freely (the engine bypasses the guard when there's no
  current route); for a ship with a route, default the origin to its destination
  but note re-route is deferred.
- **Destinations** — an ordered list of `(system, body, layover)` rows; add/remove/
  reorder. **Min-layover (UI-enforced):** non-`military` ships default each layover
  to ≥ 2 h (editable; the value we expect to vary — 007). Military default 0.
- **Plan** → `POST /plan` → preview: draw the planned legs as a path on the map +
  a summary (ETA, arrival, leg count) + the **Ship Timeline** (reused). Re-plan on
  edits.
- **Submit** → `POST /fleet/routes` with `filed`; on success the ship joins the
  live board/map and the planner clears. Surface 409 (at-origin guard) / 422 plainly.
- **Abort** — `DELETE /fleet/{tp}/route` for a selected active ship (from the board
  or planner).

### Pure logic (testable)
- `defaultLayover(military)` and the waypoint-list → `PlanRequest` mapping
  (Vitest), kept out of the components.

## Scope

1. Engine: `Universe.ships()` + `GET /fleet/ships` (catalog incl. `military`,
   `has_active_route`); schema + OpenAPI + test.
2. UI: Flight Planner panel (menu `m`); ship/origin/destination pickers; min-layover
   defaulting; Plan → preview (map path + summary + timeline); Submit; Abort.
3. Pure helpers + Vitest; api client (`fetchShipCatalog`, `postPlan`,
   `postFleetRoute`, `deleteRoute`).
4. `just check` + `just contracts` green; deploy + demo (plan + file a fresh
   multi-stop run, watch it fly).

## Out of scope (later / 028)

- **Re-routing a moving ship** / "extend from destination" — 028 (the at-origin
  guard rejects an in-flight re-file; needs a future/queued-route concept).
- **Saved/named routes**, **non-traditional waypoints** (belt points, custom
  approach) — 028.
- **Click-the-map-to-pick a destination** — nice stretch if cheap; else a follow-up.
- **Min-layover enforced in the engine** — stays UI policy (007).
- **Full Observer/Controller mode shell** (distinct chrome) — v1 is a panel.

## Tasks

- [ ] Engine: `Universe.ships()`; `GET /fleet/ships` catalog (+ `military`,
      `has_active_route`); schema + OpenAPI + test.
- [ ] Flight Planner panel + `m` to open; ship/origin/destination pickers.
- [ ] Min-layover defaulting (non-military ≥2 h, editable) + waypoint→PlanRequest.
- [ ] Plan (`POST /plan`) → map path preview + summary + Ship Timeline; re-plan on edit.
- [ ] Submit (`POST /fleet/routes`) → joins the live board; Abort (`DELETE`).
- [ ] Vitest (layover/mapping) + engine catalog test; `just check` + `just contracts`
      green; deploy + demo.

## Acceptance criteria

- From the UI: pick an idle ship, set an origin + ≥1 destination with a layover,
  Plan to preview the route (path + ETA + timeline), Submit, and see it appear on
  the live board/map.
- Multi-destination + per-waypoint layovers work end-to-end (027 reuses 026's
  multi-waypoint `/plan`); non-military ships get the default min-layover.
- In-flight ships are flagged; submitting one surfaces the guard (409) cleanly
  (re-route deferred). Abort removes an active route.
- `GET /fleet/ships` lists the catalog; `just check` + `just contracts` green;
  deployed + demoed.

## Notes / decisions

- **Controller = Observer + write.** Reuse the map, board, panels, Ship Timeline;
  the only new surface is the planner + the catalog endpoint.
- **Idle ships are the primary target** — the deployed service only knows a ship's
  location once it's filed, so origin is user-picked; the engine accepts a fresh
  route for an idle ship without the guard. Re-routing the already-under-way is 028.
- Keeps the **plan/file split** (026): always preview before committing.
